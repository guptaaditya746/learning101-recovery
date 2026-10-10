from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import Graph, URIRef

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:  # graceful fallback
    Console = None
    Panel = None
    Table = None


KG = "https://example.org/thesis-demo/kg/"


@dataclass(frozen=True)
class EdgeFact:
    edge: str
    source: str
    edge_type: str
    target: str
    chunk_id: str
    paper_id: str | None = None
    section: str | None = None
    sentence: str | None = None


def local_name(uri: str) -> str:
    text = str(uri)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def sparql_literal(value: str) -> str:
    return json.dumps(value)


def sparql_uri(value: str) -> str:
    return f"<{value}>"


def load_chunks(path: Path) -> dict[str, dict[str, Any]]:
    chunks: dict[str, dict[str, Any]] = {}

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}") from exc

            chunk_id = (
                obj.get("chunk_id")
                or obj.get("id")
                or obj.get("chunkId")
                or obj.get("chunk")
            )

            if not chunk_id:
                continue

            chunks[str(chunk_id)] = obj

    return chunks


def chunk_text(chunk: dict[str, Any]) -> str:
    for key in ("text", "content", "chunk_text", "body"):
        value = chunk.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def chunk_preview(chunk: dict[str, Any], max_chars: int = 450) -> str:
    text = chunk_text(chunk)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def run_query(g: Graph, query: str) -> list[Any]:
    return list(g.query(query))


def rows_to_facts(rows: list[Any]) -> list[EdgeFact]:
    facts: list[EdgeFact] = []

    for row in rows:
        facts.append(
            EdgeFact(
                edge=str(row.edge),
                source=str(row.src),
                edge_type=str(row.edgeType),
                target=str(row.dst),
                chunk_id=str(row.chunkId),
                paper_id=str(row.paperId) if row.paperId else None,
                section=str(row.section) if row.section else None,
                sentence=str(row.sentence) if row.sentence else None,
            )
        )

    return facts


def query_seed_facts(g: Graph, seed_chunk_ids: list[str]) -> tuple[str, list[EdgeFact]]:
    values = " ".join(sparql_literal(chunk_id) for chunk_id in seed_chunk_ids)

    query = f"""
PREFIX kg: <{KG}>

SELECT ?edge ?src ?edgeType ?dst ?chunkId ?paperId ?section ?sentence
WHERE {{
  VALUES ?chunkId {{ {values} }}

  ?edge a kg:EdgeAssertion ;
        kg:chunk_id ?chunkId ;
        kg:sourceNode ?src ;
        kg:targetNode ?dst ;
        kg:edgeType ?edgeType .

  OPTIONAL {{ ?edge kg:paper_id ?paperId . }}
  OPTIONAL {{ ?edge kg:section ?section . }}
  OPTIONAL {{ ?edge kg:sentence ?sentence . }}
}}
ORDER BY ?chunkId ?edgeType
"""

    return query, rows_to_facts(run_query(g, query))


def query_neighbor_facts(
    g: Graph,
    seed_facts: list[EdgeFact],
    limit: int,
) -> tuple[str | None, list[EdgeFact]]:
    nodes = sorted(
        {
            fact.source
            for fact in seed_facts
        }
        | {
            fact.target
            for fact in seed_facts
        }
    )

    seed_edges = sorted({fact.edge for fact in seed_facts})

    if not nodes:
        return None, []

    node_values = " ".join(sparql_uri(node) for node in nodes)

    # Exclude the seed edges so the neighborhood section shows genuinely expanded facts.
    edge_filter = ""
    if seed_edges:
        edge_values = ", ".join(sparql_uri(edge) for edge in seed_edges)
        edge_filter = f"FILTER(?edge NOT IN ({edge_values}))"

    query = f"""
PREFIX kg: <{KG}>

SELECT DISTINCT ?edge ?src ?edgeType ?dst ?chunkId ?paperId ?section ?sentence
WHERE {{
  VALUES ?node {{ {node_values} }}

  ?edge a kg:EdgeAssertion ;
        kg:sourceNode ?src ;
        kg:targetNode ?dst ;
        kg:chunk_id ?chunkId ;
        kg:edgeType ?edgeType .

  {{
    ?edge kg:sourceNode ?node .
  }}
  UNION
  {{
    ?edge kg:targetNode ?node .
  }}

  {edge_filter}

  OPTIONAL {{ ?edge kg:paper_id ?paperId . }}
  OPTIONAL {{ ?edge kg:section ?section . }}
  OPTIONAL {{ ?edge kg:sentence ?sentence . }}
}}
ORDER BY ?chunkId ?edgeType
LIMIT {limit}
"""

    return query, rows_to_facts(run_query(g, query))


def print_plain(
    question: str,
    seed_chunk_ids: list[str],
    seed_facts: list[EdgeFact],
    neighbor_facts: list[EdgeFact],
    chunks: dict[str, dict[str, Any]],
    show_sparql: bool,
    seed_query: str,
    neighbor_query: str | None,
) -> None:
    print("\nQUESTION")
    print(question)

    print("\nSEED CHUNK IDS")
    for chunk_id in seed_chunk_ids:
        print(f"- {chunk_id}")

    print("\nSEED GRAPH FACTS")
    for fact in seed_facts:
        print(
            f"- {local_name(fact.source)} "
            f"{fact.edge_type} "
            f"{local_name(fact.target)} "
            f"[chunk={fact.chunk_id}]"
        )

    print("\nEXPANDED GRAPH NEIGHBORHOOD")
    for fact in neighbor_facts:
        print(
            f"- {local_name(fact.source)} "
            f"{fact.edge_type} "
            f"{local_name(fact.target)} "
            f"[chunk={fact.chunk_id}]"
        )

    evidence_chunk_ids = sorted(
        {fact.chunk_id for fact in seed_facts + neighbor_facts}
    )

    print("\nHYDRATED EVIDENCE CHUNKS")
    for chunk_id in evidence_chunk_ids:
        chunk = chunks.get(chunk_id)
        print(f"\n--- {chunk_id} ---")
        if not chunk:
            print("[missing from chunks.jsonl]")
            continue
        print(chunk_preview(chunk))

    print("\nANSWER STUB")
    print(
        "No LLM synthesis yet. Use the seed facts, expanded graph neighborhood, "
        "and hydrated chunks above as the traceable evidence bundle."
    )

    if show_sparql:
        print("\nSPARQL: SEED FACTS")
        print(seed_query)

        if neighbor_query:
            print("\nSPARQL: NEIGHBOR FACTS")
            print(neighbor_query)


def print_rich(
    question: str,
    seed_chunk_ids: list[str],
    seed_facts: list[EdgeFact],
    neighbor_facts: list[EdgeFact],
    chunks: dict[str, dict[str, Any]],
    show_sparql: bool,
    seed_query: str,
    neighbor_query: str | None,
) -> None:
    console = Console()

    console.print(Panel(question, title="Question"))

    console.print(Panel("\n".join(seed_chunk_ids), title="Seed chunk IDs"))

    seed_table = Table(title="Seed graph facts")
    seed_table.add_column("Source")
    seed_table.add_column("Edge")
    seed_table.add_column("Target")
    seed_table.add_column("Chunk")
    seed_table.add_column("Paper")

    for fact in seed_facts:
        seed_table.add_row(
            local_name(fact.source),
            fact.edge_type,
            local_name(fact.target),
            fact.chunk_id,
            fact.paper_id or "",
        )

    console.print(seed_table)

    neighbor_table = Table(title="Expanded graph neighborhood")
    neighbor_table.add_column("Source")
    neighbor_table.add_column("Edge")
    neighbor_table.add_column("Target")
    neighbor_table.add_column("Chunk")
    neighbor_table.add_column("Paper")

    for fact in neighbor_facts:
        neighbor_table.add_row(
            local_name(fact.source),
            fact.edge_type,
            local_name(fact.target),
            fact.chunk_id,
            fact.paper_id or "",
        )

    console.print(neighbor_table)

    evidence_chunk_ids = sorted(
        {fact.chunk_id for fact in seed_facts + neighbor_facts}
    )

    for chunk_id in evidence_chunk_ids:
        chunk = chunks.get(chunk_id)
        if not chunk:
            body = "[missing from chunks.jsonl]"
        else:
            paper_id = chunk.get("paper_id", "")
            section = chunk.get("section", "")
            body = (
                f"paper_id: {paper_id}\n"
                f"section: {section}\n\n"
                f"{chunk_preview(chunk)}"
            )

        console.print(Panel(body, title=f"Hydrated evidence: {chunk_id}"))

    console.print(
        Panel(
            "No LLM synthesis yet. Use the seed facts, expanded graph neighborhood, "
            "and hydrated chunks above as the traceable evidence bundle.",
            title="Answer stub",
        )
    )

    if show_sparql:
        console.print(Panel(seed_query, title="SPARQL: seed facts"))
        if neighbor_query:
            console.print(Panel(neighbor_query, title="SPARQL: neighbor facts"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="No-LLM graph-aware retrieval expansion over RDF EdgeAssertions."
    )
    parser.add_argument(
        "question",
        help="User question. Used for trace display only in this first version.",
    )
    parser.add_argument(
        "--seed-chunk",
        action="append",
        default=[],
        help="Seed chunk ID. Can be repeated.",
    )
    parser.add_argument(
        "--graph",
        default="graph/latest_graph.ttl",
        help="Path to Turtle RDF graph.",
    )
    parser.add_argument(
        "--chunks",
        default="data/chunks.jsonl",
        help="Path to chunks JSONL.",
    )
    parser.add_argument(
        "--neighbor-limit",
        type=int,
        default=25,
        help="Maximum number of expanded neighbor facts.",
    )
    parser.add_argument(
        "--show-sparql",
        action="store_true",
        help="Print SPARQL queries used for traceability.",
    )

    args = parser.parse_args()

    if not args.seed_chunk:
        raise SystemExit(
            "Please provide at least one --seed-chunk for this milestone.\n"
            "Example:\n"
            '  python scripts/10_graph_expand_no_llm.py "What does LightRAG propose?" '
            "--seed-chunk lightrag_chunk_0030 --show-sparql"
        )

    graph_path = Path(args.graph)
    chunks_path = Path(args.chunks)

    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_path}")

    g = Graph()
    g.parse(graph_path, format="turtle")

    chunks = load_chunks(chunks_path)

    seed_query, seed_facts = query_seed_facts(g, args.seed_chunk)
    neighbor_query, neighbor_facts = query_neighbor_facts(
        g,
        seed_facts=seed_facts,
        limit=args.neighbor_limit,
    )

    if Console is not None:
        print_rich(
            question=args.question,
            seed_chunk_ids=args.seed_chunk,
            seed_facts=seed_facts,
            neighbor_facts=neighbor_facts,
            chunks=chunks,
            show_sparql=args.show_sparql,
            seed_query=seed_query,
            neighbor_query=neighbor_query,
        )
    else:
        print_plain(
            question=args.question,
            seed_chunk_ids=args.seed_chunk,
            seed_facts=seed_facts,
            neighbor_facts=neighbor_facts,
            chunks=chunks,
            show_sparql=args.show_sparql,
            seed_query=seed_query,
            neighbor_query=neighbor_query,
        )


if __name__ == "__main__":
    main()
