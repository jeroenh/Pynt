# -*- coding: utf-8 -*-
"""The IDC module contains a reader that can parse IDC XML files.""" 
import xml.sax
import os
import logging

import pynt.input
import pynt.input.rdf
import pynt.xmlns
import pynt.rangeset

nmwgns      = pynt.xmlns.GetCreateWellKnownNamespace("nmwgt")
ns = None

def setNamespace(namespace):
    global ns
    ns = namespace


class IdcReader(object):
    def __init__(self, filename):
        self.filename = filename
        # Read Technologies.
        path = os.path.realpath(os.path.normpath(os.path.join(os.path.dirname(__file__), '../schema/rdf')))
        if not os.path.isdir(path):
            path = 'http://www.science.uva.nl/research/sne/schema'
        fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/ethernet.rdf")
        fetcher.fetch()
        self.read()
        
    def read(self,filename=None):
        if filename:
            self.filename = filename
        parser = xml.sax.make_parser()
        parser.setFeature(xml.sax.handler.feature_namespaces, 1)
        parser.setContentHandler(IdcXmlHandler())
        parser.parse(self.filename)

    def getNamespace(self):
        global ns
        return ns


class IdcXmlHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.chars = []
        self.links = {}
        self._inLink = False
        self.domainID = None
        self.multiLinks = []
    
    # sax parses string values one char at a time.
    # We record each char into a temp variable, and then get it back
    # later with charValue(), which automatically clears it.
    def characters(self, content):
        self.chars.append(content)
    
    def charValue(self):
        res = (''.join(self.chars)).strip()
        self.chars = []
        return res
    
    def startElementNS(self, name, qname, attrs):
        if   name[1] == "domain":
            self.domainId = attrs.getValueByQName("id")
            # self.ns = pynt.xmlns.XMLNamespace(domainId)
            self.ns = pynt.xmlns.XMLNamespace("")
            setNamespace(self.ns)
            self.domain = pynt.elements.GetCreateAdminDomain(self.domainId,self.ns)
            if hasattr(self,"idcId"):
                self.domain.setDescription("idcId = %s" % self.idcId)
        elif name[1] == "node":
            self.nodeId = attrs.getValueByQName("id")
            self.node = pynt.elements.GetCreateDevice(self.nodeId,self.ns)
            self.node.setDomain(self.domain)
            if self.nodeId.startswith(self.domainId):
                self.node.setName(self.nodeId.replace(self.domainId+":node=",""))
            # self.chars = []
        elif name[1] == "port":
            self.portId = attrs.getValueByQName("id")
            self.port = pynt.xmlns.GetCreateRDFObject(self.portId, \
                    namespace=ns, klass=pynt.elements.StaticInterface)
            if self.portId.startswith(self.nodeId):
                self.port.setName(self.portId.replace(self.nodeId+":port=",""))
            self.port.setDevice(self.node)
            # We set link to None, so that we can check for its non-existence 
            # in the properties parsing. (they share some of the same props)
            self.link = None
        elif name[1] == "link":
            self._inLink = True
            linkId = attrs.getValueByQName("id")
            # We have to check for multi-link ports.
            # If they are, we also store them separately for later processing..
            if self.link:
                self.multiLinks += [self.link.identifier, linkId]
            self.link = Link(linkId, self.port, self.node)
            if linkId.startswith(self.portId):
                self.link.setName(linkId.replace(self.nodeId+":port=",""))
        else:
            # Clear charValue gunk that may gather because of unknown 
            # elements or whitespace.
            self.charValue()
    
    def endElementNS(self, name, qname):
        if   name[1] == "address":
            self.node.addRDFProperty(nmwgns, "address", self.charValue())
        elif name[1] == "capacity":
            if self._inLink:
                self.link.setCapacity(self.charValue())
            elif self.port:
                self.port.setCapacity(self.charValue())
        elif name[1] == "maximumReservableCapacity":
            if self._inLink:
                self.link.setMaximumReservableCapacity(self.charValue())
            elif self.port:
                self.port.setMaximumReservableCapacity(self.charValue())
        elif name[1] == "minimumReservableCapacity":
            if self._inLink:
                self.link.setMinimumReservableCapacity(self.charValue())
            elif self.port:
                self.port.setMinimumReservableCapacity(self.charValue())
        elif name[1] == "granularity":
            if self._inLink:
                self.link.setGranularity(self.charValue())
            elif self.port:
                self.port.setGranularity(self.charValue())
        elif name[1] == "remoteLinkId":
            val = self.charValue()
            if not val == u"urn:ogf:network:domain=*:node=*:port=*:link=*":
                self.link.setRemoteLinkId(val)
        elif name[1] == "trafficEngineeringMetric":
            self.link.setMetric(self.charValue())
        elif name[1] == "switchingcapType":
            self.link.setSwitchingcapType(self.charValue())
        elif name[1] == "encodingType":
            self.link.setEncodingType(self.charValue())
        elif name[1] == "interfaceMTU":
            self.link.setInterfaceMTU(self.charValue())
        elif name[1] == "vlanRangeAvailability":
            val = self.charValue()
            if val == "any": val = "0-4095"
            self.link.setVlanRangeAvailability(val)
        elif name[1] == "link":
            self._inLink = False
            # We store all the links until the end, after which we really 
            # create them.
            self.storeLink(self.link)
        elif name[1] == "node":
            self.domain.addDevice(self.node)
        elif name[1] == "port":
            self.link = None
            self.port = None
        elif name[1] == "idcId":
            self.idcId = self.charValue()
        else:
            # Stuff we know about, but don't have to do anything with it.
            if name[1] not in ["switchingCapabilitySpecificInfo", \
                        "SwitchingCapabilityDescriptors","domain","topology"]:
                logging.debug("Don't know about tag: %s" % name[1])
    
    def endDocument(self):
        # Alright, all parsing is done, let's start making links.
        createLinks(self.links, self.multiLinks)
    
    def storeLink(self, link):
        if not hasattr(link,"remoteLinkId"):
            return
        else:
            self.links[link.identifier] = link
    

class Link(object):
    "Temporary link object to store some values while parsing."
    def __init__(self, identifier,port, node):
        self.identifier = identifier
        self.port = port
        self.node = node
    
    def setName(self, value):
        self.name = value
    def setCapacity(self, value):
        self.capacity       = float(value)
    def setMaximumReservableCapacity(self,value):
        self.maximumReservableCapacity = float(value)
    def setMinimumReservableCapacity(self,value):
        self.minimumReservableCapacity = float(value)
    def setGranularity(self,value):
        self.granularity = float(value)
    def setMetric(self,value):
        self.metric = value
    def setSwitchingcapType(self,value):
        self.switchingcapType = value
    def setEncodingType(self,value):
        self.encodingType = value
    def setInterfaceMTU(self, value):
        self.interfaceMTU = value
    def setVlanRangeAvailability(self,value):
        self.vlanRangeAvailability = pynt.rangeset.RangeSet(value,\
                itemtype=int, interval=1)
    def setRemoteLinkId(self,value):
        self.remoteLinkId = value


def createLinks(links, multilinks=None):
    # First we filter out all the multi-link ports
    multiLinkPorts = {}
    for linkId in multilinks:
        link = links.pop(linkId)
        if multiLinkPorts.has_key(link.port):
            multiLinkPorts[link.port].append(link)
        else:
            multiLinkPorts[link.port] = [link]
    links = createMultiLinkPorts(multiLinkPorts,links)
    while links:
        (linkId,src) = links.popitem()
        if src.encodingType.lower() in "ethernet":
            if links.has_key(src.remoteLinkId):
                dst = links.pop(src.remoteLinkId)
                assert(dst.remoteLinkId == linkId)
                createEthConnection(src,dst)
            else:
                createEthUniConnection(src)
        else:
            raise NotImplementedError("Sorry, %s encoding is not \
                        supported at this point" % src.encodingType)

def createMultiLinkPorts(multiLinkPorts, links):
    # IDC describes:
    #            linkA
    #           /
    #       port
    #           \
    #            linkB
    # 
    # In NDL we describe this as:
    # 
    #       srcPort_tag     virtPort_tag --- SM --- linkA
    #            |               |             \
    #           \ /             \ /             -- linkB
    #            |               |
    #         srcPort ----- virtPort_unt
    # 
    # Where linkA and linkB are created as normal.
    for srcPort in multiLinkPorts:
        totalRange = pynt.rangeset.RangeSet("0",itemtype=int, interval=1)
        for link in multiLinkPorts[srcPort]:
            totalRange += link.vlanRangeAvailability
        # create local adaptation inc labelset
        ethns = pynt.xmlns.GetNamespaceByPrefix("ethernet")
        ethlayer = pynt.xmlns.GetRDFObject("EthernetNetworkElement",
            namespace=ethns, klass=pynt.layers.Layer)
        srcPort.setLayer(ethlayer)
        srcPort_tag = createTaggedEthernetPort(srcPort,totalRange)
        # create virtual connected intf + SM + node
        virtNode = pynt.elements.GetCreateDevice(srcPort.getDevice().getIdentifier()+"_virt",ns)
        virtNode.setName(srcPort.getDevice().getName()+"_virt")
        virtNode.setDomain(srcPort.getDevice().getDomain())
        dstPort = srcPort.getCreateConnectedInterface(srcPort.getIdentifier()+"_virt",ns)
        dstPort.setName(srcPort.getName()+"_virt")
        dstPort.setLayer(ethlayer)
        dstPort.setDevice(virtNode)
        dstPort_tag = createTaggedEthernetPort(dstPort,totalRange)
        # Not sure if we really want to set metric here, that can have an impact on topology.
        # Bit of housekeeping, setting MTU, Metrics, and copying capacities.
        # We get the MTU from the first link object
        if multiLinkPorts[srcPort][0].interfaceMTU:
            srcPort.addRDFProperty(nmwgns,"mtu",multiLinkPorts[srcPort][0].interfaceMTU)
            dstPort.addRDFProperty(nmwgns,"mtu",multiLinkPorts[srcPort][0].interfaceMTU)
        srcPort_tag.setMetric(0)
        dstPort_tag.setMetric(0)
        copyCapacities(srcPort,[srcPort_tag,dstPort,dstPort_tag])
        # Create the connection.
        srcPort.addConnectedInterface(dstPort)
        dstPort.addConnectedInterface(srcPort)
        for link in multiLinkPorts[srcPort]:
            # We've created a virtual node for the port:
            link.node = virtNode
            # Create the virtual srcPort
            # Bit messy shortcut using getCreateConnectedInterface
            virtSrcPort = dstPort.getCreateConnectedInterface(link.identifier+"_unt")
            virtSrcPort.setName(link.name+"_unt")
            virtSrcPort.setLayer(ethlayer)
            virtSrcPort.setDevice(virtNode)
            link.port = virtSrcPort
            if links.has_key(link.remoteLinkId):
                dstLink = links.pop(link.remoteLinkId)
                createEthConnection(link,dstLink)
            else:
                createEthUniConnection(link)
    return links
        
def copyCapacities(srcPort,dstList):
    for dst in dstList:
        dst.setCapacity(srcPort.getCapacity())
        dst.setMaximumReservableCapacity(srcPort.getMaximumReservableCapacity())
        dst.setMinimumReservableCapacity(srcPort.getMinimumReservableCapacity())
        dst.setGranularity(srcPort.getGranularity())
        # srcPort_tag.setMetric(linkobj.metric)
        
def createEthConnection(src,dst):
    """Create a bi-directional Ethernet connection.

    This function takes a src and dst link object and creates an ethernet 
    connection between them.
    """
    assert(src.encodingType == dst.encodingType)
    srcPort = createEthernetPort(src)
    dstPort = createEthernetPort(dst)
    srcPort.addConnectedInterface(dstPort)
    dstPort.addConnectedInterface(srcPort)

def createEthUniConnection(src):
    srcPort = createEthernetPort(src)
    dstPort = srcPort.getCreateConnectedInterface(src.remoteLinkId,ns)
    srcPort.addConnectedInterface(dstPort)

def createTaggedEthernetPort(port,vlanRangeAvailability,identifier=None):
    if not identifier:
        identifier = port.getIdentifier()+"_tag"
    port_tag  = pynt.xmlns.GetCreateRDFObject(identifier, \
                    namespace=ns, klass=pynt.elements.PotentialMuxInterface)
    port_tag.setName(port.getName()+"_tag")
    port_tag.setDevice(port.getDevice())
    ethns = pynt.xmlns.GetNamespaceByPrefix("ethernet")
    ethlayer = pynt.xmlns.GetRDFObject("EthernetNetworkElement",
        namespace=ethns, klass=pynt.layers.Layer)
    ethineth = pynt.xmlns.GetRDFObject("Tagged-Ethernet",
        namespace=ethns, klass=pynt.layers.AdaptationFunction)
    port_tag.setLayer(ethlayer)
    port_tag.setLabelSet(vlanRangeAvailability)
    port.addClientInterface(port_tag, ethineth)
    sm = pynt.elements.GetCreateSwitchMatrix(port.getDevice().getIdentifier()+"_sm", 
            namespace=ns)
    sm.setLayer(ethlayer)
    sm.setDevice(port.getDevice())
    sm.setSwitchingCapability(True)
    sm.setSwappingCapability(False)
    sm.setUnicast(False)
    sm.setBroadcast(True)
    sm.addInterface(port_tag)
    return port_tag
    
def createEthernetPort(linkobj):
    ethns = pynt.xmlns.GetNamespaceByPrefix("ethernet")
    ethlayer = pynt.xmlns.GetRDFObject("EthernetNetworkElement",
        namespace=ethns, klass=pynt.layers.Layer)
    ethineth = pynt.xmlns.GetRDFObject("Tagged-Ethernet",
        namespace=ethns, klass=pynt.layers.AdaptationFunction)
    port_unt = linkobj.port
    port_unt.setLayer(ethlayer)
    port_unt.setLabel(None)
    # Create the Potentially Tagged port
    port_tag = createTaggedEthernetPort(port_unt,linkobj.vlanRangeAvailability,linkobj.identifier)
    # port_tag.addRDFProperty(nmwgns,"vlanRangeAvailability", linkobj.vlanRangeAvailability)
    # Set all the collected values
    port_tag.setName(linkobj.name)
    port_tag.setCapacity(linkobj.capacity)
    port_tag.setMaximumReservableCapacity(linkobj.maximumReservableCapacity)
    port_tag.setMinimumReservableCapacity(linkobj.minimumReservableCapacity)
    port_tag.setGranularity(linkobj.granularity)
    port_tag.setMetric(linkobj.metric)
    # Set the MTU size on the parent interface
    port_unt.addRDFProperty(nmwgns,"mtu",linkobj.interfaceMTU)
    # Add the SwitchMatrix
    return port_unt



    