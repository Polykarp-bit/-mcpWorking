from __future__ import annotations

import re
from typing import Any, Dict, List

from ..core import (
    logger,
    mcp,
    _clean_content,
    _extract_title_and_content,
    _format_error,
    _run_read,
    _safe_str,
)
from .common import validate_required


# --- Analysis Tools (Explain Node, Consistency Checks) ---


@mcp.tool()
def explain_node(title: str, *, parent_name: str) -> str:
    """Erkläre einen spezifischen Dokumentations-Knoten inkl. Kontext."""
    try:
        title = validate_required(title, "title")
    except ValueError as e:
        return _format_error("explain_node", e)

    logger.info("Tool explain_node: '%s'", title)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[]-(n) "
        "WHERE "
        "  n.title = $title OR "
        "  n.name = $title OR "
        "  n.begriff = $title OR "
        "  n.roleOrName = $title OR "
        "  n.konvention = $title OR "
        "  n.randbedingung = $title OR "
        "  n.anforderung = $title OR "
        "  n.qualitaetsscenario = $title OR "
        "  n.qualitaetsziel = $title "
        "WITH DISTINCT n "
        "LIMIT 1 "
        "OPTIONAL MATCH (n)-[r]-(m) "
        "RETURN n, labels(n) AS labels, "
        "       collect({rel: type(r), other: m, otherLabels: labels(m)}) AS edges"
    )

    try:
        records = _run_read(cypher, parent_name=parent_name, title=title)
        if not records:
            return f"## Not Found\n\nKein Knoten mit Titel '{title}' gefunden.\n"

        rec = records[0]
        node = rec["n"]
        labels = rec["labels"]
        node_data = dict(node.items())
        main_title, content = _extract_title_and_content(node_data, labels)

        lines: List[str] = []
        lines.append(f"## Knoten-Erklärung: {main_title}\n")
        lines.append("### Typ und Eigenschaften\n")
        lines.append(f"- **Labels:** {', '.join(labels)}")
        for k, v in node_data.items():
            if isinstance(v, (bytes, bytearray)):
                continue
            if k in ("bildPath", "uxfPath"):
                continue
            lines.append(f"- **{k}**: {_clean_content(str(v))}")

        if content:
            lines.append("\n### Hauptinhalt\n")
            lines.append(content)

        edges = rec.get("edges") or []
        if edges:
            lines.append("\n### Direkte Beziehungen\n")
            for edge in edges:
                rel = edge.get("rel")
                other = edge.get("other")
                other_labels = edge.get("otherLabels") or []
                if other is None or rel is None:
                    continue
                other_data = dict(other.items())
                other_title, _ = _extract_title_and_content(other_data, other_labels)
                lines.append(
                    f"- `-{rel}-` → **{other_title}** "
                    f"({', '.join(other_labels) if other_labels else 'Unknown'})"
                )
        else:
            lines.append("\n### Direkte Beziehungen\n")
            lines.append("_(keine direkten Nachbarn gefunden)_")

        return "\n".join(lines) + "\n"
    except Exception as e:
        return _format_error("explain_node", e)


@mcp.tool()
def check_consistency_report(parent_name: str) -> str:
    """Führt einfache, aber konkrete Konsistenzchecks über mehrere Kapitel aus."""
    logger.info("Tool check_consistency_report aufgerufen")

    try:
        risks_records = _run_read(
            "MATCH (d:Arc42 {name: $parent_name})-[:hasRisiko]->(r:Risiko) "
            "RETURN r.anforderung AS anforderung",
            parent_name=parent_name,
        )
        risk_ids: List[str] = []
        for r in risks_records:
            desc = _safe_str(r.get("anforderung"), "")
            m = re.match(r"(RI-\\d+)", desc)
            if m:
                risk_ids.append(m.group(1))

        qs_records = _run_read(
            "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityScenario]->(q:Qualitaetsscenario) "
            "RETURN q.qualitaetsscenario AS name, q.risk AS risk_text",
            parent_name=parent_name,
        )

        covered_risks: Dict[str, bool] = {rid: False for rid in risk_ids}
        inconsistent_qs: List[str] = []

        risk_id_pattern = re.compile(r"(RI-\\d+)")
        for rec in qs_records:
            qs_name = _safe_str(rec.get("name"), "")
            risk_text = _safe_str(rec.get("risk_text"), "")
            refs = set(risk_id_pattern.findall(risk_text))
            if not refs:
                continue
            for rid in refs:
                if rid in covered_risks:
                    covered_risks[rid] = True
                else:
                    inconsistent_qs.append(
                        f"- Qualitätsszenario **{qs_name}** verweist auf unbekanntes Risiko `{rid}`."
                    )

        qs_no_qz = _run_read(
            "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityScenario]->(q:Qualitaetsscenario) "
            "WHERE NOT (q)-[:konkretisiert]->(:Qualitaetsziel) "
            "RETURN q.qualitaetsscenario AS name",
            parent_name=parent_name,
        )

        lines: List[str] = []
        lines.append("# Konsistenzbericht\n")

        lines.append("## Risiken ohne abdeckendes Qualitätsszenario\n")
        missing = [rid for rid, covered in covered_risks.items() if not covered]
        if missing:
            for rid in missing:
                lines.append(f"- Risiko `{rid}` wird von keinem Qualitätsszenario referenziert.")
        else:
            lines.append("_(keine gefunden)_")

        lines.append("\n## Qualitätsszenarien mit ungültigen Risiko-Referenzen\n")
        if inconsistent_qs:
            lines.extend(inconsistent_qs)
        else:
            lines.append("_(keine gefunden)_")

        lines.append("\n## Qualitätsszenarien ohne Qualitätsziel-Verknüpfung\n")
        if qs_no_qz:
            for rec in qs_no_qz:
                lines.append(f"- Qualitätsszenario **{_safe_str(rec.get('name'), '')}** ist nicht mit einem Qualitätsziel verknüpft.")
        else:
            lines.append("_(keine gefunden)_")

        return "\n".join(lines) + "\n"
    except Exception as e:
        return _format_error("check_consistency_report", e)

