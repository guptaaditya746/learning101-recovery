from pathlib import Path
from typing import Literal
import hashlib
import json
import re

from pydantic import BaseModel, Field, ValidationError


CHUNKS_FILE = Path("data/chunks.jsonl")
OUT_FILE = Path("data/graph_patch.json")


NodeType = Literal[
    "Paper",
    "Method",
    "Dataset",
    "Task",
    "Claim",
    "Evidence",
    "Limitation",
    "Metric",
    "Benchmark",
]

EdgeType = Literal[
    "PROPOSES",
    "ADDRESSES_TASK",
    "EVALUATES_ON",
    "MAKES_CLAIM",
    "SUPPORTED_BY",
    "HAS_LIMITATION",
    "DESCRIBES",
]


class KGNode(BaseModel):
    id: str
    type: NodeType
    label: str
    provenance: dict = Field(default_factory=dict)


class KGEdge(BaseModel):
    source: str
    target: str
    type: EdgeType
    provenance: dict = Field(default_factory=dict)


class GraphPatch(BaseModel):
    nodes: list[KGNode]
    edges: list[KGEdge]


def stable_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.lower().strip().encode("utf-8")).hexdigest()[:12]
    safe = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower().strip())[:40].strip("_")
    if not safe:
        safe = "item"
    return f"{prefix}_{safe}_{digest}"


def clean_label(text: str, max_len: int = 120) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" .,:;()[]{}")
    return text[:max_len].strip()


def sentence_split(text: str) -> list[str]:
    rough = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in rough if len(s.strip()) > 30]


def add_node(nodes_by_id: dict, node: KGNode):
    if node.id not in nodes_by_id:
        nodes_by_id[node.id] = node


def add_edge(edges_seen: set, edges: list[KGEdge], edge: KGEdge):
    key = (edge.source, edge.target, edge.type)
    if key not in edges_seen:
        edges.append(edge)
        edges_seen.add(key)


def load_chunks():
    chunks = []
    with CHUNKS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks


def extract_candidate_method(sentence: str) -> str | None:
    patterns = [
        r"\bwe propose ([^.;:]{4,120})",
        r"\bwe present ([^.;:]{4,120})",
        r"\bwe introduce ([^.;:]{4,120})",
        r"\bthis paper proposes ([^.;:]{4,120})",
        r"\bthis work proposes ([^.;:]{4,120})",
    ]

    lower = sentence.lower()

    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            return clean_label(match.group(1))

    return None


def extract_candidate_task(sentence: str) -> str | None:
    patterns = [
        r"\bfor ([a-zA-Z0-9 ,\-]{4,80})",
        r"\bto address ([a-zA-Z0-9 ,\-]{4,80})",
        r"\btackle[s]? ([a-zA-Z0-9 ,\-]{4,80})",
    ]

    lower = sentence.lower()

    task_keywords = [
        "retrieval",
        "question answering",
        "knowledge graph",
        "graph construction",
        "query",
        "reasoning",
        "generation",
    ]

    if not any(k in lower for k in task_keywords):
        return None

    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            return clean_label(match.group(1), max_len=80)

    return None


def extract_candidate_dataset(sentence: str) -> str | None:
    patterns = [
        r"\bon ([A-Z][A-Za-z0-9_\-]{2,}(?:, [A-Z][A-Za-z0-9_\-]{2,})*)",
        r"\bdataset[s]? such as ([A-Za-z0-9_, \-]{4,100})",
        r"\bbenchmark[s]? such as ([A-Za-z0-9_, \-]{4,100})",
    ]

    lower = sentence.lower()
    if not any(k in lower for k in ["dataset", "benchmark", "evaluate", "experiment"]):
        return None

    for pattern in patterns:
        match = re.search(pattern, sentence)
        if match:
            return clean_label(match.group(1), max_len=100)

    return None


def is_claim_sentence(sentence: str) -> bool:
    lower = sentence.lower()
    claim_markers = [
        "results show",
        "experiments show",
        "we demonstrate",
        "we show that",
        "outperforms",
        "improves",
        "achieves",
        "effective",
    ]
    return any(marker in lower for marker in claim_markers)


def is_limitation_sentence(sentence: str) -> bool:
    lower = sentence.lower()
    markers = [
        "limitation",
        "limitations",
        "future work",
        "fails to",
        "cannot",
        "challenging",
        "we leave",
    ]
    return any(marker in lower for marker in markers)


def main():
    chunks = load_chunks()

    nodes_by_id: dict[str, KGNode] = {}
    edges: list[KGEdge] = []
    edges_seen = set()

    for chunk in chunks:
        paper_id = chunk["paper_id"]
        chunk_id = chunk["chunk_id"]
        text = chunk["text"]

        paper_node_id = f"paper_{paper_id}"

        add_node(
            nodes_by_id,
            KGNode(
                id=paper_node_id,
                type="Paper",
                label=paper_id,
                provenance={
                    "paper_id": paper_id,
                    "source_file": chunk.get("source_file"),
                },
            ),
        )

        evidence_node_id = f"evidence_{chunk_id}"

        add_node(
            nodes_by_id,
            KGNode(
                id=evidence_node_id,
                type="Evidence",
                label=f"Evidence from {chunk_id}",
                provenance={
                    "paper_id": paper_id,
                    "chunk_id": chunk_id,
                    "section": chunk.get("section"),
                    "source_file": chunk.get("source_file"),
                    "text_preview": text[:300],
                },
            ),
        )

        add_edge(
            edges_seen,
            edges,
            KGEdge(
                source=paper_node_id,
                target=evidence_node_id,
                type="DESCRIBES",
                provenance={"paper_id": paper_id, "chunk_id": chunk_id},
            ),
        )

        for sentence in sentence_split(text):
            sent_prov = {
                "paper_id": paper_id,
                "chunk_id": chunk_id,
                "section": chunk.get("section"),
                "sentence": sentence[:500],
            }

            method = extract_candidate_method(sentence)
            if method:
                method_id = stable_id("method", method)

                add_node(
                    nodes_by_id,
                    KGNode(
                        id=method_id,
                        type="Method",
                        label=method,
                        provenance=sent_prov,
                    ),
                )

                add_edge(
                    edges_seen,
                    edges,
                    KGEdge(
                        source=paper_node_id,
                        target=method_id,
                        type="PROPOSES",
                        provenance=sent_prov,
                    ),
                )

                add_edge(
                    edges_seen,
                    edges,
                    KGEdge(
                        source=method_id,
                        target=evidence_node_id,
                        type="SUPPORTED_BY",
                        provenance=sent_prov,
                    ),
                )

            task = extract_candidate_task(sentence)
            if task and method:
                task_id = stable_id("task", task)

                add_node(
                    nodes_by_id,
                    KGNode(
                        id=task_id,
                        type="Task",
                        label=task,
                        provenance=sent_prov,
                    ),
                )

                add_edge(
                    edges_seen,
                    edges,
                    KGEdge(
                        source=method_id,
                        target=task_id,
                        type="ADDRESSES_TASK",
                        provenance=sent_prov,
                    ),
                )

            dataset = extract_candidate_dataset(sentence)
            if dataset:
                dataset_id = stable_id("dataset", dataset)

                add_node(
                    nodes_by_id,
                    KGNode(
                        id=dataset_id,
                        type="Dataset",
                        label=dataset,
                        provenance=sent_prov,
                    ),
                )

                add_edge(
                    edges_seen,
                    edges,
                    KGEdge(
                        source=paper_node_id,
                        target=dataset_id,
                        type="EVALUATES_ON",
                        provenance=sent_prov,
                    ),
                )

            if is_claim_sentence(sentence):
                claim_label = clean_label(sentence, max_len=180)
                claim_id = stable_id("claim", claim_label)

                add_node(
                    nodes_by_id,
                    KGNode(
                        id=claim_id,
                        type="Claim",
                        label=claim_label,
                        provenance=sent_prov,
                    ),
                )

                add_edge(
                    edges_seen,
                    edges,
                    KGEdge(
                        source=paper_node_id,
                        target=claim_id,
                        type="MAKES_CLAIM",
                        provenance=sent_prov,
                    ),
                )

                add_edge(
                    edges_seen,
                    edges,
                    KGEdge(
                        source=claim_id,
                        target=evidence_node_id,
                        type="SUPPORTED_BY",
                        provenance=sent_prov,
                    ),
                )

            if is_limitation_sentence(sentence):
                limitation_label = clean_label(sentence, max_len=180)
                limitation_id = stable_id("limitation", limitation_label)

                add_node(
                    nodes_by_id,
                    KGNode(
                        id=limitation_id,
                        type="Limitation",
                        label=limitation_label,
                        provenance=sent_prov,
                    ),
                )

                add_edge(
                    edges_seen,
                    edges,
                    KGEdge(
                        source=paper_node_id,
                        target=limitation_id,
                        type="HAS_LIMITATION",
                        provenance=sent_prov,
                    ),
                )

                add_edge(
                    edges_seen,
                    edges,
                    KGEdge(
                        source=limitation_id,
                        target=evidence_node_id,
                        type="SUPPORTED_BY",
                        provenance=sent_prov,
                    ),
                )

    patch = GraphPatch(nodes=list(nodes_by_id.values()), edges=edges)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        patch.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(f"Wrote graph patch: {OUT_FILE}")
    print(f"Nodes: {len(patch.nodes)}")
    print(f"Edges: {len(patch.edges)}")


if __name__ == "__main__":
    try:
        main()
    except ValidationError as e:
        print("Graph patch validation failed:")
        print(e)
        raise SystemExit(1)
