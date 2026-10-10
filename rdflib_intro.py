from rdflib import Graph

# Create an empty RDF graph
g = Graph()

print("DEBUG: Created Graph object")
print("DEBUG: g =", g)
print("DEBUG: type(g) =", type(g))
print("DEBUG: Graph length before parsing =", len(g))

# Load RDF data into the graph
url = "http://www.w3.org/People/Berners-Lee/card"
print("\nDEBUG: Parsing RDF data from:", url)

g.parse(url)

print("\nDEBUG: Finished parsing")
print("DEBUG: Graph length after parsing =", len(g))
print("DEBUG: type(g) =", type(g))

print("\n==============================")
print("DEBUG: Inspecting triples")
print("==============================")

# Loop through triples in the graph
for index, (subj, pred, obj) in enumerate(g, start=1):
    print(f"\nTriple #{index}")

    print("Subject:")
    print("  value =", subj)
    print("  type  =", type(subj))

    print("Predicate:")
    print("  value =", pred)
    print("  type  =", type(pred))

    print("Object:")
    print("  value =", obj)
    print("  type  =", type(obj))

    # This checks whether the triple exists in the graph
    if (subj, pred, obj) not in g:
        raise Exception("This triple should exist in the graph")

    # Stop early so output is not huge
    if index == 10:
        print("\nDEBUG: Stopping after 10 triples to avoid too much output")
        break

print("\n==============================")
print("Graph summary")
print("==============================")

# Print the number of triples/statements in the graph
print(f"Graph g has {len(g)} statements.")

print("\n==============================")
print("Namespaces")
print("==============================")

for prefix, namespace in g.namespaces():
    print("prefix:", prefix)
    print("namespace:", namespace)
    print()

print("\n==============================")
print("Graph in Turtle format")
print("==============================")

print(g.serialize(format="turtle"))
