from __future__ import annotations

from typing import Any, Dict, List

from ..core import (
    logger,
    mcp,
    _extract_title_and_content,
    _format_doc,
    _format_error,
    _run_read,
    _safe_str,
)


@mcp.tool()
def search_docs(query: str) -> str:
    """Sucht in allen arc42-Dokumentationsknoten (Case-Insensitive).

    Durchsucht Titel, Beschreibungen, Inhalte und alle Text-Eigenschaften.
    Gibt bis zu 50 passende Ergebnisse im Markdown-Format zurück.

    Args:
        query: Suchbegriff (z.B. 'Bausteinsicht', 'Sicherheit').
    """
    q = _safe_str(query).strip()
    if not q:
        return "## Search Results\n\nProvide a non-empty `query`.\n"

    logger.info("LLM sucht Dokumentation: '%s'", q)

    cypher = (
        "MATCH (n) "
        "WHERE ("
        "  (n.content IS NOT NULL AND toLower(n.content) CONTAINS toLower($search_term)) OR "
        "  (n.text IS NOT NULL AND toLower(n.text) CONTAINS toLower($search_term)) OR "
        "  (n.beschreibung IS NOT NULL AND toLower(n.beschreibung) CONTAINS toLower($search_term)) OR "
        "  (n.erlaeuterung IS NOT NULL AND toLower(n.erlaeuterung) CONTAINS toLower($search_term)) OR "
        "  (n.hintergrund IS NOT NULL AND toLower(n.hintergrund) CONTAINS toLower($search_term)) OR "
        "  (n.title IS NOT NULL AND toLower(n.title) CONTAINS toLower($search_term)) OR "
        "  (n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($search_term)) OR "
        "  (n.begriff IS NOT NULL AND toLower(n.begriff) CONTAINS toLower($search_term)) OR "
        "  (n.aufgabe IS NOT NULL AND toLower(n.aufgabe) CONTAINS toLower($search_term)) OR "
        "  (n.anforderung IS NOT NULL AND toLower(n.anforderung) CONTAINS toLower($search_term)) OR "
        "  (n.strategy IS NOT NULL AND toLower(n.strategy) CONTAINS toLower($search_term)) OR "
        "  (n.loesung IS NOT NULL AND toLower(n.loesung) CONTAINS toLower($search_term))"
        ") "
        "RETURN n, labels(n) AS labels "
        "LIMIT 50"
    )

    try:
        records = _run_read(cypher, search_term=q)
        rows: List[Dict[str, Any]] = []
        for record in records:
            node = record["n"]
            labels = record["labels"]
            node_data = dict(node.items())
            title, content = _extract_title_and_content(node_data, labels)
            rows.append({"title": title, "content": content, "node_type": labels[0] if labels else "Unknown"})

        if not rows:
            return f"## Search Results\n\nNo matches for `{q}`.\n"

        parts = [f"## Search Results\n\nQuery: `{q}`\n\nMatches: **{len(rows)}**\n"]
        for row in rows:
            title = _safe_str(row.get("title"), "Untitled")
            content = _safe_str(row.get("content"), "")
            node_type = _safe_str(row.get("node_type"), "")
            parts.append(_format_doc(title, content, node_type))
        return "\n".join(parts).strip() + "\n"

    except Exception as e:
        return _format_error("search_docs", e)


@mcp.tool()
def list_titles() -> str:
    """Listet alle Knotentitel der arc42-Dokumentation alphabetisch sortiert auf.

    Gibt eine Markdown-Liste aller eindeutigen Titel/Namen in der Datenbank zurück.
    Nützlich, um sich einen Überblick über die verfügbare Dokumentation zu verschaffen.
    """
    logger.info("LLM fordert Titelliste an")
    cypher = (
        "MATCH (n) "
        "RETURN n, labels(n) AS labels "
        "LIMIT 1000"
    )

    try:
        records = _run_read(cypher)
        titles_set = set()
        for record in records:
            node = record["n"]
            labels = record["labels"]
            node_data = dict(node.items())
            title, _ = _extract_title_and_content(node_data, labels)
            if title and title != "Untitled":
                titles_set.add(title)

        titles = sorted(list(titles_set), key=str.lower)

        if not titles:
            return "## Titles\n\nNo titles found.\n"

        lines = "\n".join(f"- {t}" for t in titles)
        return f"## Titles\n\nCount: **{len(titles)}**\n\n{lines}\n"

    except Exception as e:
        return _format_error("list_titles", e)

