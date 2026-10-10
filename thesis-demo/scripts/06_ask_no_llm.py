#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from llama_index.core.schema import MetadataMode, TextNode
from llama_index.retrievers.bm25 import BM25Retriever
from rdflib import Graph
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks.jsonl"
DEFAULT_GRAPH_PATH = PROJECT_ROOT / "graph" / "latest_graph.ttl"

console = Console()


# -----------------------------
# General helpers
# -----------------------------

def compact_text(text: str, max_chars: int = 420) -> str:
    clean = re.sub(r"\s+", " ", str(text)).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "…"


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def first_present(record: dict[str, Any], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return default


# -----------------------------
# Chunk loading and hydration
# -----------------------------

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing chunks file: {path}")

    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Bad JSONL at {path}:{line_no}: {e}") from e

    return rows


def get_chunk_text(chunk: dict[str, Any]) -> str:
    return first_present(
        chunk,
        ["text", "chunk_text", "content", "body", "source_text"],
        default="",
    )


def get_chunk_id(chunk: dict[str, Any], index: int) -> str:
    return first_present(
        chunk,
        ["chunk_id", "id", "uid", "node_id"],
        default=f"chunk_{index:05d}",
    )


def get_paper_id(chunk: dict[str, Any]) -> str:
    return first_present(
        chunk,
        ["paper_id", "paper", "doc_id", "document_id", "source"],
        default="unknown_paper",
    )


def get_section(chunk: dict[str, Any]) -> str:
    return first_present(
        chunk,
        ["section", "section_title", "heading"],
        default="unknown",
    )


def build_chunk_lookup(chunks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}

    for index, chunk in enumerate(chunks):
        chunk_id = get_chunk_id(chunk, index)
        lookup[chunk_id] = chunk

        # Also index common aliases if they exist.
        for key in ["id", "uid", "node_id"]:
            value = chunk.get(key)
            if value:
                lookup[str(value)] = chunk

    return lookup


def hydrate_chunk(
    chunk_lookup: dict[str, dict[str, Any]],
    chunk_id: str | None,
) -> dict[str, Any] | None:
    if not chunk_id:
        return None

    return chunk_lookup.get(chunk_id)


# -----------------------------
# LlamaIndex BM25 retrieval
# -----------------------------

def chunks_to_llama_nodes(chunks: list[dict[str, Any]]) -> list[TextNode]:
    nodes: list[TextNode] = []

    for index, chunk in enumerate(chunks):
        text = get_chunk_text(chunk)
        if not text.strip():
            continue

        chunk_id = get_chunk_id(chunk, index)

        metadata = {
            "chunk_id": chunk_id,
            "paper_id": get_paper_id(chunk),
            "section": get_section(chunk),
        }

        node = TextNode(
            id_=chunk_id,
            text=text,
            metadata=metadata,
        )

        nodes.append(node)

    return nodes


def llama_bm25_search(
    question: str,
    chunks: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    nodes = chunks_to_llama_nodes(chunks)

    if not nodes:
        return []

    retriever = BM25Retriever.from_defaults(
        nodes=nodes,
        similarity_top_k=top_k,
    )

    hits = retriever.retrieve(question)

    results: list[dict[str, Any]] = []

    for rank, hit in enumerate(hits, start=1):
        node = hit.node
        metadata = dict(node.metadata or {})

        text = node.get_content(metadata_mode=MetadataMode.NONE)

        results.append(
            {
                "rank": rank,
                "score": float(hit.score or 0.0),
                "chunk_id": safe_str(metadata.get("chunk_id"), node.node_id),
                "paper_id": safe_str(metadata.get("paper_id"), "unknown_paper"),
                "section": safe_str(metadata.get("section"), "unknown"),
                "text": text,
                "preview": compact_text(text),
            }
        )

    return results


# -----------------------------
# Intent detection
# -----------------------------

INTENT_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "paper_proposes",
        "triggers": ["propose", "proposes", "proposed", "introduce", "introduces", "present", "presents"],
        "edge_types": ["PROPOSES"],
    },
    {
        "name": "paper_claims",
        "triggers": ["claim", "claims", "argue", "argues", "show", "shows", "demonstrate"],
        "edge_types": ["MAKES_CLAIM"],
    },
    {
        "name": "paper_limitations",
        "triggers": ["limitation", "limitations", "weakness", "weaknesses", "fail", "fails"],
        "edge_types": ["HAS_LIMITATION"],
    },
    {
        "name": "paper_evaluates",
        "triggers": ["evaluate", "evaluates", "evaluation", "benchmark", "dataset", "metric"],
        "edge_types": ["EVALUATES_ON"],
    },
    {
        "name": "paper_tasks",
        "triggers": ["task", "tasks", "address", "addresses"],
        "edge_types": ["ADDRESSES_TASK"],
    },
]


def detect_intent(question: str) -> dict[str, Any]:
    q = question.lower()

    for pattern in INTENT_PATTERNS:
        if any(trigger in q for trigger in pattern["triggers"]):
            return pattern

    return {
        "name": "general_graph_lookup",
        "triggers": [],
        "edge_types": [
            "PROPOSES",
            "MAKES_CLAIM",
            "SUPPORTED_BY",
            "HAS_LIMITATION",
            "EVALUATES_ON",
            "ADDRESSES_TASK",
            "USES_METHOD",
            "DESCRIBES",
        ],
    }


def extract_entity_hint(question: str) -> str | None:
    stopwords = {
        "What", "Which", "Who", "When", "Where", "Why", "How",
        "Does", "Do", "Did", "Are", "Is", "Was", "Were",
        "The", "A", "An", "Of", "For", "In", "On", "To",
    }

    candidates = re.findall(
        r"\b[A-Z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*(?:\s+[A-Z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*)*",
        question,
    )

    candidates = [candidate.strip() for candidate in candidates if candidate.strip() not in stopwords]

    if candidates:
        return max(candidates, key=len)

    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', question)
    flattened = [a or b for a, b in quoted]

    if flattened:
        return flattened[0].strip()

    return None


# -----------------------------
# RDF graph and SPARQL
# -----------------------------

def load_graph(path: Path) -> Graph:
    if not path.exists():
        raise FileNotFoundError(f"Missing RDF graph: {path}")

    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def sparql_string_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def make_assertion_query(
    edge_types: list[str],
    entity_hint: str | None,
    limit: int,
) -> tuple[str, str]:
    edge_filters = " || ".join(
        f'LCASE(STR(?edgeType)) = "{edge_type.lower()}"'
        for edge_type in edge_types
    )

    entity_filter = ""

    if entity_hint:
        entity = sparql_string_literal(entity_hint.lower())
        entity_filter = f"""
        FILTER(
            CONTAINS(LCASE(COALESCE(STR(?sLabel), "")), "{entity}")
            || CONTAINS(LCASE(COALESCE(STR(?oLabel), "")), "{entity}")
            || CONTAINS(LCASE(STR(?s)), "{entity}")
            || CONTAINS(LCASE(STR(?o)), "{entity}")
            || CONTAINS(LCASE(COALESCE(STR(?paper), "")), "{entity}")
        )
        """

    query_name = "edge_assertion_with_provenance"

    query = f"""
PREFIX kg: <https://example.org/thesis-demo/kg/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?assertion ?s ?sLabel ?p ?edgeType ?o ?oLabel ?paper ?section ?chunk ?preview ?sentence
WHERE {{
    ?assertion a kg:EdgeAssertion ;
               rdf:subject ?s ;
               rdf:predicate ?p ;
               rdf:object ?o ;
               kg:edgeType ?edgeType .

    OPTIONAL {{ ?s rdfs:label ?sLabel . }}
    OPTIONAL {{ ?o rdfs:label ?oLabel . }}

    OPTIONAL {{ ?assertion kg:paper_id ?paper . }}
    OPTIONAL {{ ?assertion kg:section ?section . }}
    OPTIONAL {{ ?assertion kg:chunk_id ?chunk . }}
    OPTIONAL {{ ?assertion kg:text_preview ?preview . }}
    OPTIONAL {{ ?assertion kg:sentence ?sentence . }}

    FILTER({edge_filters})

    {entity_filter}
}}
LIMIT {limit}
"""

    return query_name, query


def local_name(uri_or_value: Any) -> str:
    text = str(uri_or_value)

    if "#" in text:
        return text.rsplit("#", 1)[-1]

    if "/" in text:
        return text.rstrip("/").rsplit("/", 1)[-1]

    return text


def run_assertion_query(
    graph: Graph,
    edge_types: list[str],
    entity_hint: str | None,
    limit: int,
) -> dict[str, Any]:
    query_name, query = make_assertion_query(
        edge_types=edge_types,
        entity_hint=entity_hint,
        limit=limit,
    )

    try:
        results = list(graph.query(query))
    except Exception as e:
        return {
            "query_name": query_name,
            "query": query,
            "rows": [],
            "error": str(e),
        }

    rows: list[dict[str, Any]] = []

    for row in results:
        subject_label = safe_str(row.sLabel, local_name(row.s))
        object_label = safe_str(row.oLabel, local_name(row.o))

        rows.append(
            {
                "assertion": safe_str(row.assertion),
                "subject": subject_label,
                "predicate": local_name(row.p),
                "edge_type": safe_str(row.edgeType),
                "object": object_label,
                "paper_id": safe_str(row.paper),
                "section": safe_str(row.section),
                "chunk_id": safe_str(row.chunk),
                "rdf_preview": safe_str(row.preview) or safe_str(row.sentence),
            }
        )

    return {
        "query_name": query_name,
        "query": query,
        "rows": rows,
        "error": None,
    }


# -----------------------------
# Hydration layer
# -----------------------------

def hydrate_graph_rows(
    graph_rows: list[dict[str, Any]],
    chunk_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    hydrated: list[dict[str, Any]] = []

    for row in graph_rows:
        chunk_id = row.get("chunk_id")
        chunk = hydrate_chunk(chunk_lookup, chunk_id)

        hydrated_row = dict(row)

        if chunk:
            hydrated_row["hydrated"] = True
            hydrated_row["hydrated_text"] = get_chunk_text(chunk)
            hydrated_row["hydrated_preview"] = compact_text(get_chunk_text(chunk), 520)
            hydrated_row["hydrated_paper_id"] = get_paper_id(chunk)
            hydrated_row["hydrated_section"] = get_section(chunk)
        else:
            hydrated_row["hydrated"] = False
            hydrated_row["hydrated_text"] = ""
            hydrated_row["hydrated_preview"] = compact_text(row.get("rdf_preview", ""), 520)
            hydrated_row["hydrated_paper_id"] = row.get("paper_id", "")
            hydrated_row["hydrated_section"] = row.get("section", "")

        hydrated.append(hydrated_row)

    return hydrated


# -----------------------------
# Answer stub
# -----------------------------

def sentence_score(question: str, sentence: str) -> int:
    q_terms = set(re.findall(r"[A-Za-z0-9_+-]+", question.lower()))
    s_terms = set(re.findall(r"[A-Za-z0-9_+-]+", sentence.lower()))
    return len(q_terms.intersection(s_terms))


def best_sentence(question: str, text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    if not sentences:
        return compact_text(text, 420)

    ranked = sorted(sentences, key=lambda s: sentence_score(question, s), reverse=True)
    return compact_text(ranked[0], 420)


def make_answer_stub(
    question: str,
    bm25_results: list[dict[str, Any]],
    graph_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    if graph_rows:
        lines.append("Graph facts:")
        for row in graph_rows[:5]:
            lines.append(
                f"- {row['subject']} --{row['edge_type']}--> {row['object']} "
                f"[{row.get('paper_id') or row.get('hydrated_paper_id')}, {row.get('chunk_id')}]"
            )
    else:
        lines.append("Graph facts: no matching assertion rows found.")

    lines.append("")

    hydrated_evidence = [row for row in graph_rows if row.get("hydrated_preview")]

    if hydrated_evidence:
        lines.append("Hydrated graph evidence:")
        for row in hydrated_evidence[:3]:
            lines.append(
                f"- [{row.get('paper_id') or row.get('hydrated_paper_id')} / "
                f"{row.get('section') or row.get('hydrated_section')} / "
                f"{row.get('chunk_id')}] "
                f"{best_sentence(question, row.get('hydrated_text') or row.get('hydrated_preview'))}"
            )
    elif bm25_results:
        top = bm25_results[0]
        lines.append("Top BM25 evidence:")
        lines.append(
            f"- [{top['paper_id']} / {top['section']} / {top['chunk_id']}] "
            f"{best_sentence(question, top['text'])}"
        )

    lines.append("")
    lines.append(
        "Answer stub: no LLM synthesis yet. The answer should be derived only from "
        "the graph facts and hydrated evidence shown above."
    )

    return "\n".join(lines)


# -----------------------------
# Rich printing
# -----------------------------

def print_trace_header(
    question: str,
    intent: dict[str, Any],
    entity_hint: str | None,
    query_name: str,
    chunk_count: int,
) -> None:
    console.print(
        Panel.fit(
            f"[bold]Question[/bold]\n{question}\n\n"
            f"[bold]Detected intent[/bold]\n{intent['name']}\n\n"
            f"[bold]Edge templates[/bold]\n{', '.join(intent['edge_types'])}\n\n"
            f"[bold]Entity hint[/bold]\n{entity_hint or 'none'}\n\n"
            f"[bold]Chunks loaded[/bold]\n{chunk_count}\n\n"
            f"[bold]SPARQL query name[/bold]\n{query_name}",
            title="Trace header",
        )
    )


def print_bm25_table(rows: list[dict[str, Any]]) -> None:
    table = Table(title="Text retrieval: LlamaIndex BM25")

    table.add_column("Rank", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Paper")
    table.add_column("Section")
    table.add_column("Chunk")
    table.add_column("Preview")

    for row in rows:
        table.add_row(
            str(row["rank"]),
            f"{row['score']:.4f}",
            row["paper_id"],
            row["section"],
            row["chunk_id"],
            row["preview"],
        )

    console.print(table)


def print_graph_table(rows: list[dict[str, Any]]) -> None:
    table = Table(title="Graph retrieval: SPARQL EdgeAssertions")

    table.add_column("Subject")
    table.add_column("Edge")
    table.add_column("Object")
    table.add_column("Paper")
    table.add_column("Section")
    table.add_column("Chunk")
    table.add_column("Hydrated?")

    for row in rows:
        table.add_row(
            compact_text(row["subject"], 80),
            row["edge_type"],
            compact_text(row["object"], 80),
            row.get("paper_id") or row.get("hydrated_paper_id") or "",
            row.get("section") or row.get("hydrated_section") or "",
            row.get("chunk_id") or "",
            "yes" if row.get("hydrated") else "no",
        )

    console.print(table)


def print_hydrated_evidence(rows: list[dict[str, Any]]) -> None:
    table = Table(title="Hydrated graph evidence from chunks.jsonl")

    table.add_column("Fact")
    table.add_column("Chunk")
    table.add_column("Evidence preview")

    for row in rows:
        fact = f"{row['subject']} --{row['edge_type']}--> {row['object']}"
        preview = row.get("hydrated_preview") or row.get("rdf_preview") or ""

        table.add_row(
            compact_text(fact, 100),
            row.get("chunk_id") or "",
            compact_text(preview, 520),
        )

    console.print(table)


# -----------------------------
# CLI
# -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="No-LLM ask pipeline using LlamaIndex BM25 + RDFLib SPARQL + chunk hydration."
    )

    parser.add_argument("question", help="Question to ask, wrapped in quotes.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--graph-limit", type=int, default=20)
    parser.add_argument("--show-sparql", action="store_true")

    args = parser.parse_args()

    chunks = load_jsonl(args.chunks)
    chunk_lookup = build_chunk_lookup(chunks)

    graph = load_graph(args.graph)

    intent = detect_intent(args.question)
    entity_hint = extract_entity_hint(args.question)

    bm25_rows = llama_bm25_search(
        question=args.question,
        chunks=chunks,
        top_k=args.top_k,
    )

    graph_result = run_assertion_query(
        graph=graph,
        edge_types=intent["edge_types"],
        entity_hint=entity_hint,
        limit=args.graph_limit,
    )

    hydrated_graph_rows = hydrate_graph_rows(
        graph_rows=graph_result["rows"],
        chunk_lookup=chunk_lookup,
    )

    console.rule("[bold]No-LLM GraphRAG Ask Pipeline[/bold]")

    print_trace_header(
        question=args.question,
        intent=intent,
        entity_hint=entity_hint,
        query_name=graph_result["query_name"],
        chunk_count=len(chunks),
    )

    print_bm25_table(bm25_rows)

    if args.show_sparql:
        console.print(
            Panel(
                Syntax(graph_result["query"].strip(), "sparql", theme="ansi_dark"),
                title="Generated SPARQL",
            )
        )

    if graph_result["error"]:
        console.print(
            Panel(
                graph_result["error"],
                title="SPARQL error",
                style="red",
            )
        )
        return

    print_graph_table(hydrated_graph_rows)
    print_hydrated_evidence(hydrated_graph_rows)

    answer_stub = make_answer_stub(
        question=args.question,
        bm25_results=bm25_rows,
        graph_rows=hydrated_graph_rows,
    )

    console.print(
        Panel(
            answer_stub,
            title="Answer stub",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
