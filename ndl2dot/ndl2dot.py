#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import distutils.version
# semi-standard modules
try:
    import rdflib
except ImportError:
    raise ImportError("Module rdflib is not available. It can be downloaded from http://rdflib.net/\n")
if distutils.version.StrictVersion(rdflib.__version__) < "2.0.9":
    raise ImportError("The installed version of rdflib, %s, is too old. 2.1 or higher is required" % rdflib.__version__)
from rdflib.Graph import Graph
from rdflib.sparql.sparqlGraph  import SPARQLGraph
from rdflib.sparql.graphPattern import GraphPattern
global rdfcompatmode
if distutils.version.StrictVersion(rdflib.__version__) > "2.3.9":
    rdfcompatmode = False
    from rdflib.sparql import Query
else:
    rdfcompatmode = True

# Define NDL namespace as a global variable
global ndl,rdf,rdfs
ndl  = rdflib.Namespace("http://www.science.uva.nl/research/sne/ndl#")
rdf  = rdflib.Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
rdfs = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")
global bindings
bindings = { u"ndl": ndl, u"rdf": rdf, u"rdfs": rdfs }

def getConnections(graph):
    """
    Given a NDL triplet graph, return lists of external and
    internal connections.
    
    The method runs a SPARQL query on the graph.
    Next step is to filter out the equivalent connections, which is done using a
    stack, because lists cannot be altered while iterating over them.
    
    Difference between internal and external is currently based on whether the
    symmetric connectedTo property is present in the graph.
    
    The results are beautified using the getHostName method.
    """
    global rdf,rdfs,ndl,bindings,rdfcompatmode
    select = ("?ifA","?ifB")
    where = GraphPattern([
            ("?ifA", ndl["connectedTo"], "?ifB"),
            ("?ifB", ndl["connectedTo"], "?ifA"),
            ])
    # Create a SPARQLGraph wrapper object out of the normal Graph
    sparqlGrph = SPARQLGraph(graph)
    # Make the query
    if rdfcompatmode:
        result = sparqlGrph.query(select, where)
    else:
        result = Query.query(sparqlGrph, select, where, initialBindings=bindings)
    #print "Found %d connections" % len(result)
    internalConnections = []
    externalConnections = []
    while len(result) > 0:
        ifA,ifB = result.pop()
        if (ifB,ifA) in result:
            result.remove((ifB,ifA))
            internalConnections.append((getHostName(graph,ifA), getHostName(graph,ifB)))
        else:
            externalConnections.append((getHostName(graph,ifA), getHostName(graph,ifB)))
    locations = getLocations(graph)
    return internalConnections, externalConnections, locations

def getLocations(graph):
    locations = []
    global rdf,rdfs,ndl,bindings,rdfcompatmode
    sparqlGrph = SPARQLGraph(graph)
    for loc in graph.subjects(predicate=rdf["type"], object=ndl["Location"]):
        select = ("?hostName")
        where = [GraphPattern([
                ("?hostUri", ndl["locatedAt"], loc),
                ("?hostUri", ndl["name"], "?hostName"),
                ]),
            GraphPattern([
                ("?hostUri", ndl["locatedAt"], loc),
                ("?hostUri", rdfs["label"], "?hostName"),
                ])]
        # Create a SPARQLGraph wrapper object out of the normal Graph
        # Make the query
        if rdfcompatmode:
            result = sparqlGrph.query(select, where)
        else:
            result = Query.query(sparqlGrph, select, where, initialBindings=bindings)
        if result:
            locations.append(result)
    return locations
    
def getHostName(graph, ifUri):
    """
    Given a URI of an interface, return the name of the host
    If the host has a 'name' property, return that value.
    Otherwise, strip off the first part of the URI (until '#') and return the last part.
    """
    global rdf,rdfs,ndl,bindings,rdfcompatmode
    select = ("?hostUri","?hostName")
    where = [GraphPattern([
            ("?hostUri", ndl["hasInterface"], ifUri),
            ("?hostUri", ndl["name"], "?hostName"),
            ]),
        GraphPattern([
            ("?hostUri", ndl["hasInterface"], ifUri),
            ("?hostUri", rdfs["label"], "?hostName"),
            ])]
    # Create a SPARQLGraph wrapper object out of the normal Graph
    sparqlGrph = SPARQLGraph(graph)
    # Make the query
    if rdfcompatmode:
        result = sparqlGrph.query(select, where)
    else:
        result = Query.query(sparqlGrph, select, where, initialBindings=bindings)
    if result:
        hostUri, hostName = result[0]
        ifName = ifUri.replace(hostUri+":","")
        return (hostName,ifName)
    else:
        return (ifUri[ifUri.find("#"):],"")
    

def dotString(internal, external, locations):
    """
    Given two lists of internal and external connections, return a string suitable
    for Graphviz.
    
    All nodes are colored lightblue, connections are labelled with interfacenames at relevant
    ends.
    Internal nodes are contained in a subgraph and are shaped as rectangles.
    External nodes are ellipses.
    """
    dotString = "graph RDFS {\n"
    dotString += "\trankdir=LR;\n"
    dotString += '\t ranksep="1.2";\n'
    dotString += "\tedge [arrowhead=none];\n"
    dotString += '\tnode [label="\N", fontname=Arial, fixedsize=false, color=lightblue,style=filled];\n'
    x = 0
    for loc in locations:
        x += 1
        dotString += '\tsubgraph cluster%s {\n' % x
        dotString += '\t\tnode [shape = box];\n'
        for node in loc:
            dotString += '\t\t"%s";\n' % node
        dotString += '\t}\n'
    # # Start Processing internal nodes and connections
    # dotString += '\tsubgraph clusterInternal {\n'
    # dotString += '\t\tnode [shape = box];\n'
    # for t in internal:
    #     if len(t):
    #         (hostA,ifA),(hostB,ifB) = t
    #         dotString += '\t\t"%s" -- "%s" [taillabel = "%s", headlabel = "%s"];\n' % (hostA, hostB, ifA, ifB)
    # # End of internal connections
    # dotString += '\t}\n'
    for t in internal:
        if len(t):
            (hostA,ifA),(hostB,ifB) = t
            dotString += '\t\t"%s" -- "%s" [taillabel = "%s", headlabel = "%s"];\n' % (hostA, hostB, ifA, ifB)
    dotString += '\n\tnode [shape =ellipse];\n'
    for t in external:
        if len(t):
            (hostA,ifA),(hostB,ifB) = t
            dotString += '\t"%s" -- "%s" [taillabel = "%s", headlabel = "%s"];\n' % (hostA, hostB, ifA, ifB)
    dotString += "}"
    return dotString
    
def main(inputFileName, outputFileName=None):
    """
    Given an inputfile and optionally outputfile, create a GraphViz file of the NDL inputfile.
    
    If no outputfile is given, default to inputfilename with rdf replaced with dot.
    If the file exists, ask for user confirmation to overwrite it.
    """
    graph = Graph()
    graph.parse(inputFileName)
    internal, external, locations = getConnections(graph)
    dotStr = dotString(internal, external, locations)
    
    if not outputFileName:
        outputFileName = inputFileName.replace(".rdf",".dot")
    if os.path.exists(outputFileName):
        while True:
            arg = raw_input("%s already exists. To replace type 'y' or provide different filename: " % outputFileName)
            # Some input should be given, otherwise repeat the question.
            if arg:
                if arg in "yY":
                    # Overwrite the file
                    break
                # A new name was given, store it
                outputFileName = arg
                # Check if new file exists, if so, repeat the question, if not, write the file
                if not os.path.exists(arg):
                    break
    f = file(outputFileName,'w')
    f.write(dotStr)
    f.close()

if __name__=="__main__":
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            if len(sys.argv) > 2:
                main(sys.argv[1],sys.argv[2])
            else:
                main(sys.argv[1])
        else:
            sys.exit("The file %s was not found" % sys.argv[1])
    else:
        sys.exit("Usage: %s input-filename [output-filename]" % sys.argv[0])