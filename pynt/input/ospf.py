# -*- coding: utf-8 -*-
"""The ospf device module contains a parsers which retrieves information from ospf LSAs using the ospf input module"""

import pynt.input
import pynt.input.rdf
import pynt.protocols.ospfinput
# import pynt.protocols.lsa
import pynt.technologies.ip
import os.path

#ipns       = pynt.technologies.ip.GetNamespace()
#iplayer    = pynt.technologies.ip.GetLayer("ip")

class OspfNetworkSegmentException(Exception):
    "Raised when there is a problem creating a OSPF Network Segment."
    pass
    
class OspfFetcher(pynt.input.BaseDeviceFetcher):
    def __init__(self, *args, **params):
        pynt.input.BaseDeviceFetcher.__init__(self, *args, **params)
        self.subjectClass = pynt.elements.Domain
        self.iplayer      = pynt.technologies.ip.GetLayer("ip")
        self.connections  = {}
        self.ns           = self.namespace
        self.opaqueOnlyFlag = False
        self._ignoreStubs = False
    
    def setSourceHost(self, hostname, remoteport=2600, localport=4000):
        self.io = pynt.protocols.ospfinput.OspfNetworkInput(hostname=hostname, remoteport=remoteport, localport=localport)
    
    def setSourceFile(self, filename, hostname=None):
        self.io = pynt.protocols.ospfinput.OspfEmulatorInput(filename=filename)
    
    def retrieve(self):
        # if len(pynt.xmlns.rdfobjects) > 0:
        #     raise RuntimeWarning("pynt.xmlns.rdfobjects is non-empty. Overwriting old information.")
        # if len(pynt.xmlns.xmlnamespaces) > 0:
        #     raise RuntimeWarning("pynt.xmlns.xmlnamespaces is non-empty. Overwriting old information.")
        ReadTechnologies()
        self.parseLSAs( self.io.getLSAs() )
        # self.io.getLSAs()
    
    def parseLSAs(self, lsas):
        networkLSAs = []
        if self.opaqueOnlyFlag:
            for lsa in lsas:
                if lsa.type == 10: self.handleAreaOpaqueLSA(lsa)
        else:
            for lsa in lsas:
                if   lsa.type == 1:
                    self.handleRouterLSA(lsa)
                elif lsa.type == 2:
                    # Network LSAs are handled at the end so that all devices and interfaces (should) exist
                    networkLSAs.append(lsa)
                elif lsa.type == 5:
                    self.handleASExternalLSA(lsa)
                elif lsa.type == 10:
                    self.handleAreaOpaqueLSA(lsa)
                else:
                    raise NotImplementedError("Handing of LSA type %s is not implemented." % lsa.type)
            self.handleNetworkLSAs(networkLSAs)
        # Finished with all LSAs, so now we create the connections.
        self.createConnections(self.connections)
        
    
    def handleRouterLSA(self, lsa):
        dev = pynt.elements.GetCreateDevice("dev"+lsa.getAdvertisingRouter(), self.ns, klass=pynt.technologies.ip.RouterDevice)
        devSwitch = pynt.elements.GetCreateSwitchMatrix("dev"+lsa.getAdvertisingRouter()+"Switch", self.ns)
        devSwitch.setLayer(self.iplayer)
        devSwitch.setDevice(dev)
        devSwitch.setSwitchingCapability(True)
        for link in lsa.links:
            if link.getType() == 1:
                # Point-to-Point connection
                # Annoying kind of connection, because the only information we have is the
                # address of the *connected* interface.
                # To avoid nameclashes: we name our interface "p"+thisRouterID+"p"+otherRouterID
                # This provides a unique reproducable ID
                intf = dev.getCreateNativeInterface("p"+lsa.getAdvertisingRouter()+"p"+link.getLinkId(), self.ns)
                intf.setLayer(self.iplayer)
                intf.setIPAddress(link.getLinkData())
                # intf.setOSPFP2PInterface()
                devSwitch.addInterface(intf)
                # We would like to do the following, but to do that requires a rewrite of addConnectedInterface.
                # intf.addConnectedInterface("p"+link.getLinkId()+"p"+lsa.getAdvertisingRouter())
                connectedDev = pynt.elements.GetCreateDevice("dev"+link.getLinkId(), self.ns, klass=pynt.technologies.ip.RouterDevice)
                connectedInterface = connectedDev.getCreateNativeInterface("p"+link.getLinkId()+"p"+lsa.getAdvertisingRouter(), self.ns)
                connectedInterface.setLayer(self.iplayer)
                intf.addConnectedInterface(connectedInterface)
                intf.setMetric(link.getMetric())
            elif link.getType() == 2:
                # Transit Network
                intf = dev.getCreateNativeInterface(link.getLinkData())
                intf.setLayer(self.iplayer)
                intf.setTEAddress(link.getLinkData())
                devSwitch.addInterface(intf)
                bc = pynt.elements.GetCreateBroadcastSegment("bc"+link.getLinkId(), self.ns, klass=pynt.technologies.ip.IPBroadcastSegment)
                bc.setLayer(self.iplayer)
                intf.addConnectedInterface(bc)
                intf.setMetric(link.getMetric())
            elif link.getType() == 3:
                # Stub Network
                # To avoid nameclashes: we name our interface: "stub"+thisRouter+"net"+network
                if not self._ignoreStubs:
                    intf = dev.getCreateNativeInterface("stub"+lsa.getAdvertisingRouter()+"net"+link.getLinkId())
                    intf.setLayer(self.iplayer)
                    devSwitch.addInterface(intf)
                    bc = pynt.elements.GetCreateBroadcastSegment("stub"+link.getLinkId(), self.ns, klass=pynt.technologies.ip.IPBroadcastSegment)
                    bc.setMask(link.getLinkData())
                    bc.setLayer(self.iplayer)
                    intf.addConnectedInterface(bc)
                    intf.setMetric(link.getMetric())
            elif link.getType() == 4:
                # Virtual Link
                raise Exception("Parsing of Virtual Link data is not implemented yet.")
            # OSPF defines the metric for the link.
            # Adding a link object solely for the metric seems silly, so we add the metric to the interface.
            # This means that all metrics for paths will be double of the OSPF metric.
            else:
                raise Exception("An unknown link type (%s) has been found!" % link.getType())
        
    def handleNetworkLSAs(self, lsas):
        for lsa in lsas:
            bc = pynt.elements.GetCreateBroadcastSegment("bc"+lsa.getLinkStateId(), self.ns, klass=pynt.technologies.ip.IPBroadcastSegment)
            bc.setMask(lsa.getNetworkMask())
            # Now that we have the broadcast segment, we want to get the other routers connected to it.
            # That way we can independently confirm the connection to this broadcast segment.
            for routerId in lsa.getAttachedRouters():
                router = pynt.elements.GetCreateDevice("dev"+routerId, self.ns, klass=pynt.technologies.ip.RouterDevice)
                routerIntfs = router.getNativeInterfaces()
                connectedIntfs = [x for x in routerIntfs if bc in x.getConnectedInterfacesOnly()]
                if len(connectedIntfs) == 1:
                    bc.addConnectedInterface(connectedIntfs[0])
                else:
                    pass
                    # raise OspfNetworkSegmentException("Device %s does not have an interface in segment %s." % (router,bc))

    def handleASExternalLSA(self, lsa):
        # ASExternal LSAs are silently ignored. They do not carry topologically significant data.
        pass
    
    def handleAreaOpaqueLSA(self, lsa):
        router = pynt.elements.GetCreateDevice("dev"+lsa.getAdvertisingRouter(), self.ns)
        if lsa.tlvtype == 1:
            intf = pynt.elements.GetCreateInterface(lsa.routerAddress, self.ns, klass=pynt.technologies.ip.IPInterface)
            intf.setDevice(router)
            intf.setLayer(self.iplayer)
            intf.setIPAddress(lsa.routerAddress)
        elif lsa.tlvtype == 2:
            # First we determine the name of the interfaces by examining the link type.
            # Then we see if we need multiple layers by examining the ISCD
            # Then we create the interfaces, and add the relevant properties to them.
            connectedIntfaddr = None
            bcname = None
            encoding = None
            #### Interface Naming
            # point-to-point link
            intfaddr = None
            if lsa.subtlvs["Link type"] == 1:
                if lsa.subtlvs.has_key("Local interface"):  intfaddr = lsa.subtlvs["Local interface"][0]
                elif lsa.subtlvs.has_key("Link local ID"):  intfaddr = lsa.subtlvs["Link local ID"]
                if lsa.subtlvs.has_key("Remote interface"): connectedIntfaddr = lsa.subtlvs["Remote interface"][0]
                elif lsa.subtlvs.has_key("Link remote ID"): connectedIntfaddr = lsa.subtlvs["Link remote ID"]
            # multi-access link
            if lsa.subtlvs["Link type"] == 2:
                intfaddr = lsa.subtlvs["Local interface"][0]
                bcname = "bc" + lsa.subtlvs["Link ID"]
            # layering information
            if lsa.subtlvs.has_key("ISCD"):
                encoding = lsa.subtlvs["ISCD"].encoding
            #### Object Creation
            if intfaddr:
                if encoding:            intfname = intfaddr + getLayerNameEncoding(encoding)
                else:                   intfname = intfaddr
            else:
                intfname = "p%sp%s" % (lsa.getAdvertisingRouter(), lsa.subtlvs["Link ID"])
            intf = pynt.elements.Interface(intfname, self.ns)
            intf.setDevice(router)
            # Add some extra properties and connections.
            # if lsa.subtlvs["Link type"] == 1:
            #     intf.setOSPFTEP2PInterface()
            if intfaddr:
                intf.setTEAddress(intfaddr)
            if bcname:
                pynt.elements.GetCreateBroadcastSegment(bcname, self.ns)
                intf.addConnectedInterface(bc)
                bc.addConnectedInterface(intf)
            if encoding:
                intf.setLayer(getLayerObjectEncoding(encoding))
                if connectedIntfaddr:
                    if self.connections.has_key(intfaddr): raise Exception("Existing connection entry detected for %s" % intfaddr)
                    # Connection is created later, adaptations may be necessary.
                    self.connections[intfaddr] = (encoding, connectedIntfaddr)
                layername, layerobj = getLayerSwcap(lsa.subtlvs["ISCD"].swcap)
                swmatrix = pynt.elements.GetCreateSwitchMatrix(router.getIdentifier()+layername+"SwitchMatrix", self.ns)
                swmatrix.setDevice(router)
                swmatrix.setLayer(layerobj)
                swmatrix.setSwitchingCapability(True)
                swmatrix.setSwappingCapability(False)
                addInterfaceToSwmatrix(intf, encoding, swmatrix, lsa.subtlvs["ISCD"].swcap)
            #### Adding Properties
            if lsa.subtlvs.has_key("TE metric"):            intf.setMetric(lsa.subtlvs["TE metric"])
            # if lsa.subtlvs.has_key("Capacity"):             intf.setCapacity(lsa.subtlvs["Capacity"])
            if lsa.subtlvs.has_key("Max reservable bandwidth"): intf.setCapacity(lsa.subtlvs["Max reservable bandwidth"])
            if lsa.subtlvs.has_key("Unreserved bandwidth"):     intf.setAvailableCapacity(lsa.subtlvs["Unreserved bandwidth"][0])
            # if lsa.subtlvs.has_key("Admin group"):
            # if lsa.subtlvs.has_key("Link protection type"):
            # if lsa.subtlvs.has_key("Shared risk link group"):
            if lsa.subtlvs.has_key("Domain ID"): # DRAGON Specific value
                domain = pynt.elements.GetCreateDomain(lsa.subtlvs["Domain ID"], self.ns)
                router.setDomain(domain)

    def createConnections(self,connections):
        for srcAddr in connections:
            locEnc, trgAddr = connections[srcAddr]
            if connections.has_key(trgAddr):
                if srcAddr != connections[trgAddr][1]:
                    raise Exception("Illegal connection found for %s, %s, %s" % (srcAddr, trgAddr, connection[trgAddr][1]))
                trgEnc = connections[trgAddr][0]
                if locEnc == trgEnc:
                    commonEnc = locEnc
                elif locEnc > trgEnc:
                    commonEnc = trgEnc
                    createAdaptationInterfaces(locIntf, locEnc, commonEnc)
                elif locEnc < trgEnc:
                    commonEnc = locEnc
                    createAdaptationInterfaces(trgIntf, trgIntf, commonEnc)
                srcIntf = pynt.elements.GetCreateInterface(srcAddr+getLayerNameEncoding(commonEnc), self.ns)
                trgIntf = pynt.elements.GetCreateInterface(trgAddr+getLayerNameEncoding(commonEnc), self.ns)
                srcIntf.addConnectedInterface(trgIntf)
                trgIntf.addConnectedInterface(srcIntf)
            
# Helper functions
def ReadTechnologies():
    path = os.path.normpath(os.path.join(os.path.realpath(os.path.dirname(__file__)), '../../schema/rdf'))
    if not os.path.isdir(path):
        path = 'http://www.science.uva.nl/research/sne/schema'
    fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/ip.rdf")
    fetcher.fetch()
    fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/ethernet.rdf")
    fetcher.fetch()
    fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/tdm.rdf")
    fetcher.fetch()
    fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/wdm.rdf")
    fetcher.fetch()
    
    ipns        = pynt.xmlns.GetNamespaceByPrefix("ip")
    ethns       = pynt.xmlns.GetNamespaceByPrefix("ethernet")
    tdmns       = pynt.xmlns.GetNamespaceByPrefix("tdm")
    wdmns       = pynt.xmlns.GetNamespaceByPrefix("wdm")
    global iplayer, ethlayer, tdmlayer, lambdalayer, fiberlayer
    iplayer     = pynt.xmlns.GetRDFObject("IPNetworkElement",      namespace=ipns, klass=pynt.layers.Layer)
    ethlayer    = pynt.xmlns.GetRDFObject("EthernetNetworkElement",namespace=ethns,klass=pynt.layers.Layer)
    tdmlayer    = pynt.xmlns.GetRDFObject("OC192NetworkElement",   namespace=tdmns,klass=pynt.layers.Layer)
    lambdalayer = pynt.xmlns.GetRDFObject("LambdaNetworkElement",  namespace=wdmns,klass=pynt.layers.Layer)
    fiberlayer  = pynt.xmlns.GetRDFObject("FiberNetworkElement",   namespace=wdmns,klass=pynt.layers.Layer)

def createAdaptationInterfaces(intf, encoding, targetEncoding):
    raise NotImplementedError("External Adaptations have not been implemented yet.")
    
def addInterfaceToSwmatrix(intf, encoding, swmatrix, swcap):
    if getLayerObjectEncoding(encoding) == getLayerObjectSwcap(swcap):
        swmatrix.addInterface(intf)
    else:
        raise NotImplementedError("Internal Adaptations have not been implemented yet.")
    
def getLayerObjectEncoding(encoding):
    global iplayer, ethlayer, tdmlayer, lambdalayer, fiberlayer
    if   encoding == 1: return iplayer
    elif encoding == 2: return ethlayer
    elif encoding == 3: return tdmlayer
    elif encoding == 4: return tdmlayer
    elif encoding == 5: return None # TODO Digitalwrapper
    elif encoding == 6: return lambdalayer
    elif encoding == 7: return fiberlayer
    elif encoding == 8: return None # TODO FiberChannel
    
def getLayerNameEncoding(encoding):
    if   encoding == 1: return "IP"
    elif encoding == 2: return "Ethernet"
    elif encoding == 3: return "TDM"
    elif encoding == 4: return "TDM"
    elif encoding == 5: return "DigitalWrapper"
    elif encoding == 6: return "Lambda"
    elif encoding == 7: return "Fiber"
    elif encoding == 8: return "FiberChannel"
        
    
def getLayerSwcap(swcap):
    return getLayerNameSwcap(swcap), getLayerObjectSwcap(swcap)
    
def getLayerNameSwcap(swcap):
    if   swcap == 1: return "IP"
    elif swcap == 2: return "IP"
    elif swcap == 3: return "IP"
    elif swcap == 4: return "IP"
    elif swcap == 51: return "Ethernet"
    elif swcap == 100: return "TDM"
    elif swcap == 150: return "Lambda"
    elif swcap == 200: return "Fiber"
def getLayerObjectSwcap(swcap):
    global iplayer, ethlayer, tdmlayer, lambdalayer, fiberlayer
    if   swcap == 1: return iplayer
    elif swcap == 2: return iplayer
    elif swcap == 3: return iplayer
    elif swcap == 4: return iplayer
    elif swcap == 51: return ethlayer
    elif swcap == 100: return tdmlayer
    elif swcap == 150: return lambdalayer
    elif swcap == 200: return fiberlayer
