# -*- coding: utf-8 -*-
"""RDF module -- Input from and Output to RDF using rdflib"""

# builtin modules
import logging
# semi-standard modules
try:
    import rdflib
    if map(int, rdflib.__version__.split(".")) >= [3, 0, 0]:
        from rdflib import Literal
        from rdflib import ConjunctiveGraph as Graph
    elif map(int, rdflib.__version__.split(".")) > [2, 1, 0]:
        from rdflib.Graph import Graph
        from rdflib.Literal import Literal
except ImportError:
    raise ImportError("Module rdflib is not available. It can be downloaded from http://rdflib.net/\n")
# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns
import pynt.rangeset
import pynt.output


class RDFOutput(pynt.output.BaseOutput):
    """Output to RDF using librdf"""
    graph           = None  # the graph with the NDL data.
    format          = "pretty-xml"  # used as serialization format for rdflib. Either 'xml', 'pretty-xml' or 'n3'
    printconfigured = True
    printchildren   = True
    
    def setOutputFile(self, outfile):
        if isinstance(outfile, str):
            self.filename = outfile
            self.openfile()
        else:
            raise AttributeError("output parameter for RDFOutput.setOutput() must be a filename (not a FileType)")
    
    def openfile(self, append=False):
        """Make sure self.outfile is a valid and open FileType"""
        self.graph = Graph()
        self.outfile = self.graph  # we use the graph as the output object.
    
    def closefile(self):
        # format output and save to disk.
        self.graph.serialize(self.filename, format=self.format, encoding="utf-8")
        self.graph = None
        self.outfile = None
    
    def setPrintConfigured(self,printconfigured):
        """Print only static or also configured interfaces?"""
        self.printconfigured = bool(printconfigured)
    
    def mayPrintConfigured(self):
        """Print only static or also configured interfaces?"""
        return self.printconfigured
    
    def staticOnly(self):
        """Print only static or also configured interfaces?"""
        return not self.printconfigured
    
    def setPrintChildren(self,printchildren):
        """Print only information about an element, or also about all of it's child elements?"""
        self.printchildren = bool(printchildren)
    
    def mayPrintChildren(self):
        """Print only information about an element, or also about all of it's child elements?"""
        return self.printchildren
    
    def write(self, string):
        pass
    
    def printHeader(self):
        pass
    
    def printFooter(self):
        pass
    
    def printDevice(self, device):
        subjecturi = rdflib.URIRef(device.getURIdentifier())
        rdf  = self.GetRDFLibNamespace(prefix="rdf")
        rdfs = self.GetRDFLibNamespace(prefix="rdfs")
        ndl  = self.GetRDFLibNamespace(prefix="ndl")
        self.graph.add((subjecturi, rdf["type"], ndl["Device"]))
        
        for interface in device.getLogicalInterfaces(ordered=True):
            if self.mayPrintConfigured() or not interface.removable: # Print fixed interface always; removable only if mayPrintConfigured()
                self.graph.add((subjecturi, ndl["hasInterface"], rdflib.URIRef(interface.getURIdentifier())))
                self.printInterface(interface)
                # for connectedInterface in interface.getConnectedInterfacesOnly():
                #     self.graph.add((subjecturi, ndl["connectedTo"], rdflib.URIRef(connectedInterface.getURIdentifier())))
                #     if interface.getBroadcastSegment():
                #         self.graph.add((rdflib.URIRef(interface.getBroadcastSegment().getURIdentifier(), rdf["type"], ndl["ConnectionPoint"])))
                        

        for switchmatrix in device.getSwitchMatrices():
            pass
            # TODO: replace with self.graph.add()
            # if self.mayPrintChildren():
            #     self.write('<capability:hasSwitchMatrix>')
            #     self.printSwitchMatrix(switchmatrix)
            #     self.write('</capability:hasSwitchMatrix>')
            # else:
            #     self.write('<capability:hasSwitchMatrix rdf:resource="%s"/>' % switchmatrix.getURIdentifier())
    
    def printBroadcastSegment(self, bc):
        # self.graph.add()
        pass
    
    def printInterface(self, interface):
        subjecturi = rdflib.URIRef(interface.getURIdentifier())
        rdf  = self.GetRDFLibNamespace(prefix="rdf")
        rdfs = self.GetRDFLibNamespace(prefix="rdfs")
        ndl  = self.GetRDFLibNamespace(prefix="ndl")
        capability  = self.GetRDFLibNamespace(prefix="capability")
        
        # Type of interface
        # self.graph.add((subjecturi, rdf["type"], ndl["ConnectionPoint"]))
        if interface.isPotential:
            self.graph.add((subjecturi, rdf["type"], capability["PotentialMuxInterface"]))
        else:
            self.graph.add((subjecturi, rdf["type"], ndl["Interface"]))
        if interface.removable:
            self.graph.add((subjecturi, rdf["type"], capability["InstantiatedMuxInterface"]))
        elif interface.configurable:
            self.graph.add((subjecturi, rdf["type"], ndl["ConfigurableInterface"]))
        # Layer
        if interface.layer:
            self.write('<rdf:type rdf:resource="%s"/>' % (interface.layer.getURIdentifier()))
        else:
            self.write( '<!-- unspecified layer -->')
        # Connected, Linked and Switched interfaces
        for connectedInterface in interface.getConnectedInterfacesOnly():
            self.graph.add((subjecturi, ndl["connectedTo"], rdflib.URIRef(connectedInterface.getURIdentifier())))
        for connectedInterface in interface.getLinkedInterfacesOnly():
            self.graph.add((subjecturi, ndl["linkedTo"], rdflib.URIRef(connectedInterface.getURIdentifier())))
        for connectedInterface in interface.getDirectlySwitchedInterfaces():
            # This does not distinguish between circuit or packet switchedTo.
            self.graph.add((subjecturi, ndl["switchedTo"], rdflib.URIRef(connectedInterface.getURIdentifier())))
        # LinkSegement and SwitchMatrix
        # Switch Matrix is done for printSwitchMatrix.
        #if interface.getSwitchMatrix() != None:
        #    self.graph.add((rdflib.URIRef(interface.getSwitchMatrix().getURIdentifier()), ndl["hasInterface"], subjecturi))
        if interface.getBroadcastSegment() != None:
            self.graph.add((rdflib.URIRef(subjecturi, ndl["connectedTo"], interface.getBroadcastSegment().getURIdentifier())))
            self.graph.add((rdflib.URIRef(interface.getBroadcastSegment().getURIdentifier(), rdf["type"], ndl["BroadcastSegment"])))
        # Adapted interfaces
        
        # Generic interface properties
        
    
    def GetRDFLibNamespace(self, prefix=None, uri=None):
        if uri:
            namespace = pynt.xmlns.GetCreateNamespace(uri=uri, prefix=prefix)
        else:
            namespace = pynt.xmlns.GetCreateWellKnownNamespace(prefix, uri=uri)
        self.graph.bind(namespace.getPrefix(), namespace.uri)
        return rdflib.Namespace(namespace.uri)

