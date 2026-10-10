from rdflib import Graph

print("\n==============================")
print("1. Create graph and parse data")
print("==============================")

url = "http://www.w3.org/People/Berners-Lee/card"

print("DEBUG: URL we will parse:")
print(url)

g = Graph()

print("\nDEBUG: Empty graph created")
print("DEBUG: g =", g)
print("DEBUG: type(g) =", type(g))
print("DEBUG: len(g) before parse =", len(g))

print("\nDEBUG: Now parsing RDF data from URL...")

g.parse(url)

print("\nDEBUG: Finished parsing")
print("DEBUG: g =", g)
print("DEBUG: type(g) =", type(g))
print("DEBUG: len(g) after parse =", len(g))


print("\n==============================")
print("2. Show namespaces")
print("==============================")

for prefix, namespace in g.namespaces():
    print("prefix:", prefix)
    print("namespace:", namespace)
    print()


print("\n==============================")
print("3. Print first 10 triples")
print("==============================")

for index, (s, p, o) in enumerate(g, start=1):
    print("\n------------------------------")
    print("Triple number:", index)

    print("SUBJECT value:", s)
    print("SUBJECT type :", type(s))

    print("PREDICATE value:", p)
    print("PREDICATE type :", type(p))

    print("OBJECT value:", o)
    print("OBJECT type :", type(o))

    if index == 10:
        print("\nDEBUG: Stopping after 10 triples")
        break


print("\n==============================")
print("4. Create SPARQL query")
print("==============================")

q = """
    PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?name
    WHERE {
        ?p rdf:type foaf:Person .
        ?p foaf:name ?name .
    }
"""

print("DEBUG: SPARQL query is:")
print(q)


print("\n==============================")
print("5. Run SPARQL query")
print("==============================")

results = g.query(q)

print("DEBUG: results =", results)
print("DEBUG: type(results) =", type(results))


print("\n==============================")
print("6. Inspect query results")
print("==============================")

for index, r in enumerate(results, start=1):
    print("\n------------------------------")
    print("Result row number:", index)

    print("DEBUG: r =", r)
    print("DEBUG: type(r) =", type(r))

    print("DEBUG: r labels =", r.labels)
    print("DEBUG: r as dict-like access using ['name']")

    name = r["name"]

    print("name value:", name)
    print("name type :", type(name))

    print("\nFINAL PRINTED NAME:")
    print(name)
