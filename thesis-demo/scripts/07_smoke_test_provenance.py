#!/usr/bin/env python3

from pathlib import Path

from rdflib import Graph


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = PROJECT_ROOT / "graph" / "latest_graph.ttl"


query = """
PREFIX kg: <https://example.org/thesis-demo/kg/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?sLabel ?edgeType ?oLabel ?paper ?section ?chunk ?preview
WHERE {
  ?assertion a kg:EdgeAssertion ;
             rdf:subject ?s ;
             rdf:predicate ?p ;
             rdf:object ?o ;
             kg:edgeType ?edgeType .

  OPTIONAL { ?s rdfs:label ?sLabel . }
  OPTIONAL { ?o rdfs:label ?oLabel . }

  OPTIONAL { ?assertion kg:paper_id ?paper . }
  OPTIONAL { ?assertion kg:section ?section . }
  OPTIONAL { ?assertion kg:chunk_id ?chunk . }
  OPTIONAL { ?assertion kg:text_preview ?preview . }
}
LIMIT 10
"""


def clean(value):
    if value is None:
        return ""
    text = str(value).replace("\n", " ")
    return text[:160]


def main():
    graph = Graph()
    graph.parse(GRAPH_PATH, format="turtle")

    rows = list(graph.query(query))

    print(f"Loaded triples: {len(graph)}")
    print(f"Rows: {len(rows)}")
    print()

    for row in rows:
        print("FACT")
        print(f"  subject : {clean(row.sLabel)}")
        print(f"  edge    : {clean(row.edgeType)}")
        print(f"  object  : {clean(row.oLabel)}")
        print(f"  paper   : {clean(row.paper)}")
        print(f"  section : {clean(row.section)}")
        print(f"  chunk   : {clean(row.chunk)}")
        print(f"  preview : {clean(row.preview)}")
        print()


if __name__ == "__main__":
    main()
