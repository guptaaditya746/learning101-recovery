from pathlib import Path
import json
import re

from rdflib import Graph, Literal, Namespace, RDF, URIRef


PATCH_FILE = Path("data/graph_patch.json")
OUT_FILE = Path("graph/latest_graph.ttl")

KG = Namespace("http://example.org/kg/")
NODE = Namespace("http://example.org/node/")


def safe_uri_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\\-]", "_", value)


def node_uri(node_id: str) -> URIRef:
    return NODE[safe_uri_id(node_id)]


def main():
    patch = json.loads(PATCH_FILE.read_text(encoding="utf-8"))

    g = Graph()
    g.bind("kg", KG)
    g.bind("node", NODE)

    for node in patch["nodes"]:
        s = node_uri(node["id"])
        g.add((s, RDF.type, KG[node["type"]]))
        g.add((s, KG.label, Literal(node["label"])))

        provenance = node.get("provenance", {})
        for key, value in provenance.items():
            if value is None:
                continue
            g.add((s, KG[key], Literal(str(value))))

    for edge in patch["edges"]:
        source = node_uri(edge["source"])
        target = node_uri(edge["target"])
        predicate = KG[edge["type"]]
        g.add((source, predicate, target))

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(OUT_FILE), format="turtle")

    print(f"Wrote RDF graph: {OUT_FILE}")
    print(f"Triples: {len(g)}")


if __name__ == "__main__":
    main()
