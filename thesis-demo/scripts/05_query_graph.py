from pathlib import Path
import sys

from rdflib import Graph, Namespace


GRAPH_FILE = Path("graph/latest_graph.ttl")
KG = Namespace("http://example.org/kg/")


QUERIES = {
    "papers": """
        PREFIX kg: <http://example.org/kg/>

        SELECT ?paper ?label
        WHERE {
          ?paper a kg:Paper ;
                 kg:label ?label .
        }
        ORDER BY ?label
    """,

    "methods": """
        PREFIX kg: <http://example.org/kg/>

        SELECT ?paperLabel ?methodLabel ?evidencePreview
        WHERE {
          ?paper a kg:Paper ;
                 kg:label ?paperLabel ;
                 kg:PROPOSES ?method .

          ?method kg:label ?methodLabel ;
                  kg:SUPPORTED_BY ?evidence .

          OPTIONAL { ?evidence kg:text_preview ?evidencePreview . }
        }
        ORDER BY ?paperLabel
    """,

    "claims": """
        PREFIX kg: <http://example.org/kg/>

        SELECT ?paperLabel ?claimLabel ?evidencePreview
        WHERE {
          ?paper a kg:Paper ;
                 kg:label ?paperLabel ;
                 kg:MAKES_CLAIM ?claim .

          ?claim kg:label ?claimLabel ;
                 kg:SUPPORTED_BY ?evidence .

          OPTIONAL { ?evidence kg:text_preview ?evidencePreview . }
        }
        ORDER BY ?paperLabel
    """,

    "limitations": """
        PREFIX kg: <http://example.org/kg/>

        SELECT ?paperLabel ?limitationLabel ?evidencePreview
        WHERE {
          ?paper a kg:Paper ;
                 kg:label ?paperLabel ;
                 kg:HAS_LIMITATION ?limitation .

          ?limitation kg:label ?limitationLabel ;
                      kg:SUPPORTED_BY ?evidence .

          OPTIONAL { ?evidence kg:text_preview ?evidencePreview . }
        }
        ORDER BY ?paperLabel
    """,

    "datasets": """
        PREFIX kg: <http://example.org/kg/>

        SELECT ?paperLabel ?datasetLabel
        WHERE {
          ?paper a kg:Paper ;
                 kg:label ?paperLabel ;
                 kg:EVALUATES_ON ?dataset .

          ?dataset kg:label ?datasetLabel .
        }
        ORDER BY ?paperLabel
    """,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in QUERIES:
        print("Usage:")
        print("  python scripts/05_query_graph.py <query_name>")
        print()
        print("Available query names:")
        for name in QUERIES:
            print(f"  - {name}")
        raise SystemExit(1)

    query_name = sys.argv[1]

    g = Graph()
    g.parse(str(GRAPH_FILE), format="turtle")

    print(f"Loaded {len(g)} triples")
    print(f"Running query: {query_name}")
    print("=" * 80)

    rows = list(g.query(QUERIES[query_name]))

    if not rows:
        print("No rows returned.")
        return

    for i, row in enumerate(rows, start=1):
        print(f"\nResult {i}")
        print("-" * 80)

        for key, value in row.asdict().items():
            text = str(value)
            if len(text) > 500:
                text = text[:500] + "..."
            print(f"{key}: {text}")


if __name__ == "__main__":
    main()
