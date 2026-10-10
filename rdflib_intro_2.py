from rdflib import Graph, Literal, RDF, URIRef

# rdflib knows about quite a few popular namespaces,
# like W3C ontologies, schema.org, etc.
from rdflib.namespace import FOAF, XSD


print("\n==============================")
print("1. Creating an RDF Graph")
print("==============================")

# Create a Graph
g = Graph()

print("DEBUG: g =", g)
print("DEBUG: type(g) =", type(g))
print("DEBUG: len(g) before adding triples =", len(g))


print("\n==============================")
print("2. Inspecting imported RDF tools")
print("==============================")

print("DEBUG: RDF =", RDF)
print("DEBUG: type(RDF) =", type(RDF))

print("\nDEBUG: RDF.type =", RDF.type)
print("DEBUG: type(RDF.type) =", type(RDF.type))

print("\nDEBUG: FOAF =", FOAF)
print("DEBUG: type(FOAF) =", type(FOAF))

print("\nDEBUG: FOAF.Person =", FOAF.Person)
print("DEBUG: type(FOAF.Person) =", type(FOAF.Person))

print("\nDEBUG: FOAF.name =", FOAF.name)
print("DEBUG: type(FOAF.name) =", type(FOAF.name))

print("\nDEBUG: FOAF.nick =", FOAF.nick)
print("DEBUG: type(FOAF.nick) =", type(FOAF.nick))

print("\nDEBUG: FOAF.mbox =", FOAF.mbox)
print("DEBUG: type(FOAF.mbox) =", type(FOAF.mbox))

print("\nDEBUG: XSD =", XSD)
print("DEBUG: type(XSD) =", type(XSD))

print("\nDEBUG: XSD.string =", XSD.string)
print("DEBUG: type(XSD.string) =", type(XSD.string))

print("\nDEBUG: XSD.anyURI =", XSD.anyURI)
print("DEBUG: type(XSD.anyURI) =", type(XSD.anyURI))


print("\n==============================")
print("3. Creating URIRef subject: donna")
print("==============================")

# Create an RDF URI node to use as the subject for multiple triples
donna = URIRef("http://example.org/donna")

print("DEBUG: donna =", donna)
print("DEBUG: type(donna) =", type(donna))


print("\n==============================")
print("4. Creating Donna triples")
print("==============================")

triple1 = (donna, RDF.type, FOAF.Person)
triple2 = (donna, FOAF.nick, Literal("donna", lang="en"))
triple3 = (donna, FOAF.name, Literal("Donna Fales"))
triple4 = (donna, FOAF.mbox, URIRef("mailto:donna@example.org"))

print("\nDEBUG: triple1 =", triple1)
print("DEBUG: triple1 subject type =", type(triple1[0]))
print("DEBUG: triple1 predicate type =", type(triple1[1]))
print("DEBUG: triple1 object type =", type(triple1[2]))

print("\nDEBUG: triple2 =", triple2)
print("DEBUG: triple2 object value =", triple2[2])
print("DEBUG: triple2 object type =", type(triple2[2]))
print("DEBUG: triple2 object language =", triple2[2].language)
print("DEBUG: triple2 object datatype =", triple2[2].datatype)

print("\nDEBUG: triple3 =", triple3)
print("DEBUG: triple3 object value =", triple3[2])
print("DEBUG: triple3 object type =", type(triple3[2]))
print("DEBUG: triple3 object language =", triple3[2].language)
print("DEBUG: triple3 object datatype =", triple3[2].datatype)

print("\nDEBUG: triple4 =", triple4)
print("DEBUG: triple4 object value =", triple4[2])
print("DEBUG: triple4 object type =", type(triple4[2]))

print("\nDEBUG: Adding Donna triples to graph")

g.add(triple1)
print("DEBUG: len(g) after triple1 =", len(g))

g.add(triple2)
print("DEBUG: len(g) after triple2 =", len(g))

g.add(triple3)
print("DEBUG: len(g) after triple3 =", len(g))

g.add(triple4)
print("DEBUG: len(g) after triple4 =", len(g))


print("\n==============================")
print("5. Creating URIRef subject: ed")
print("==============================")

# Add another person
ed = URIRef("http://example.org/edward")

print("DEBUG: ed =", ed)
print("DEBUG: type(ed) =", type(ed))


print("\n==============================")
print("6. Creating Edward triples")
print("==============================")

triple5 = (ed, RDF.type, FOAF.Person)
triple6 = (ed, FOAF.nick, Literal("ed", datatype=XSD.string))
triple7 = (ed, FOAF.name, Literal("Edward Scissorhands"))
triple8 = (ed, FOAF.mbox, Literal("e.scissorhands@example.org", datatype=XSD.anyURI))

print("\nDEBUG: triple5 =", triple5)
print("DEBUG: triple5 subject type =", type(triple5[0]))
print("DEBUG: triple5 predicate type =", type(triple5[1]))
print("DEBUG: triple5 object type =", type(triple5[2]))

print("\nDEBUG: triple6 =", triple6)
print("DEBUG: triple6 object value =", triple6[2])
print("DEBUG: triple6 object type =", type(triple6[2]))
print("DEBUG: triple6 object language =", triple6[2].language)
print("DEBUG: triple6 object datatype =", triple6[2].datatype)

print("\nDEBUG: triple7 =", triple7)
print("DEBUG: triple7 object value =", triple7[2])
print("DEBUG: triple7 object type =", type(triple7[2]))
print("DEBUG: triple7 object language =", triple7[2].language)
print("DEBUG: triple7 object datatype =", triple7[2].datatype)

print("\nDEBUG: triple8 =", triple8)
print("DEBUG: triple8 object value =", triple8[2])
print("DEBUG: triple8 object type =", type(triple8[2]))
print("DEBUG: triple8 object language =", triple8[2].language)
print("DEBUG: triple8 object datatype =", triple8[2].datatype)

print("\nDEBUG: Adding Edward triples to graph")

g.add(triple5)
print("DEBUG: len(g) after triple5 =", len(g))

g.add(triple6)
print("DEBUG: len(g) after triple6 =", len(g))

g.add(triple7)
print("DEBUG: len(g) after triple7 =", len(g))

g.add(triple8)
print("DEBUG: len(g) after triple8 =", len(g))


print("\n==============================")
print("7. Final Graph Information")
print("==============================")

print("DEBUG: g =", g)
print("DEBUG: type(g) =", type(g))
print("DEBUG: total number of triples in g =", len(g))


print("\n==============================")
print("8. Printing raw triples")
print("==============================")

for index, (s, p, o) in enumerate(g, start=1):
    print("\n------------------------------")
    print("Triple number:", index)

    print("\nSUBJECT")
    print("value:", s)
    print("type :", type(s))

    print("\nPREDICATE")
    print("value:", p)
    print("type :", type(p))

    print("\nOBJECT")
    print("value:", o)
    print("type :", type(o))

    if isinstance(o, Literal):
        print("object language:", o.language)
        print("object datatype:", o.datatype)
    else:
        print("object is not a Literal")
        print("object language: not available")
        print("object datatype: not available")


print("\n==============================")
print("9. Finding all people")
print("==============================")

print("DEBUG: Searching for subjects where:")
print("predicate =", RDF.type)
print("object    =", FOAF.Person)

for person in g.subjects(RDF.type, FOAF.Person):
    print("\nFOUND PERSON")
    print("person value:", person)
    print("person type :", type(person))

    print("\nNow searching for this person's mailbox:")
    print("subject   =", person)
    print("predicate =", FOAF.mbox)

    for mbox in g.objects(person, FOAF.mbox):
        print("\nFOUND MAILBOX")
        print("mbox value:", mbox)
        print("mbox type :", type(mbox))

        if isinstance(mbox, Literal):
            print("mbox datatype:", mbox.datatype)
            print("mbox language:", mbox.language)
        else:
            print("mbox is not a Literal")
            print("mbox is probably a URIRef")


print("\n==============================")
print("10. Binding namespace prefix")
print("==============================")

print("DEBUG: Before binding, FOAF namespace is:")
print(FOAF)

g.bind("foaf", FOAF)

print("DEBUG: Bound prefix 'foaf' to namespace:")
print(FOAF)

print("\nDEBUG: Current namespaces in graph:")

for prefix, namespace in g.namespaces():
    print("prefix:", prefix, "| namespace:", namespace)


print("\n==============================")
print("11. Printing graph in Notation3 format")
print("==============================")

print(g.serialize(format="n3"))
