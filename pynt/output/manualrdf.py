# -*- coding: utf-8 -*-
"""
ManualRDFOutput -- manually formatted RDF, with predictable order of each statement
ManualRDFv22Output -- manually formatted RDF, NDL 2.2 format (obsolete)
"""

# builtin modules
import types
import xml.sax.saxutils  # to escape strings in XML
# local modules
import pynt.xmlns
import pynt.output
import pynt.elements
import pynt.technologies
import socket

import pynt.technologies.ethernet
import pynt.technologies.wdm
import pynt.technologies.tdm


class RDFOutput(pynt.output.BaseOutput):
    """manually formatted RDF"""
    printconfigured = True
    printchildren   = True
    indent          = 0
    outfile         = None
    
    def __init__(self, outfile=None, subject=None, printconfigured=True):
        pynt.output.BaseOutput.__init__(self,outfile=outfile,subject=subject)
        self.indent = 0
        self.setPrintConfigured(printconfigured)
    
    def write(self, string):
        self.outfile.write((self.indent*'    ')+str(string)+"\n")
    
    def encode(self, string):
        # string MUST be a UTF-8 encoded string, properly XML-encoded ("shoeSize < IQ" => "shoeSize &lt; IQ" etc.)
        return xml.sax.saxutils.escape(string)
    
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
    
    def getWellKnownNamespaces(self):
        """Return a list of well known namespaces, hard-coded in scripts."""
        # define all namespaces that are hard-coded in these scripts.
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='rdf')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='rdfs')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='xsd')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='dc')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='dcterms')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='vs')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='ndl')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='layer')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='capability')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='domain')
        pynt.xmlns.GetCreateWellKnownNamespace(prefix='physical')
        return pynt.xmlns.GetNamespaces()
    
    def printHeader(self):
        def namespaceSortKey(ns):
            return "%d%d%d-%s-%s" % (not ns.metaschema, not ns.layerschema, not ns.networkschema, ns.prefix, ns.uri)
        namespaces = self.getWellKnownNamespaces()
        namespaces.sort(key=namespaceSortKey)
        self.write('<?xml version="1.0" encoding="UTF-8"?>')
        self.write('<rdf:RDF')
        schemacount = 0
        for namespace in namespaces:
            if namespace.metaschema or namespace.layerschema:
                self.write('        xmlns:%s="%s"' % (namespace.getPrefix(), namespace.getURI()))
                if (namespace.getSchemaURL() or namespace.getExtraHumanURL()) and not namespace.metaschema:
                    schemacount += 1
        self.write('>')
        self.indent += 1
        self.write('')
        if schemacount > 0:
            self.write('<!-- Hi there, fancy RDF parsers, here you can get those nifty RDF schemas. Have fun parsing. -->')
            for namespace in namespaces:
                if namespace.metaschema:
                    continue # don't include pointers to rdf, rdfs, ndl, ndllayer schema, etc. Only layer or network schema
                if namespace.getSchemaURL() or namespace.getExtraHumanURL():
                    self.write('<rdf:Description rdf:about="%s">' % namespace.getURI())
                    self.indent += 1
                    if namespace.getSchemaURL():
                        self.write('<rdfs:isDefinedBy rdf:resource="%s"/> <!-- the schema -->' % namespace.getSchemaURL())
                    if namespace.getExtraHumanURL():
                        self.write('<vs:userdocs rdf:resource="%s"/> <!-- human readable info -->' % namespace.getHumanURL())
                    self.indent -= 1
                    self.write('</rdf:Description>')
            self.write('')
    
    def printDocumentMetaData(self, subject):
        metadata = self.metadata
        self.write('<rdf:Description rdf:about="">')
        self.indent += 1
        self.write('<!-- meta data on this document itself -->')
        if "title" in metadata:
            title = metadata["title"]
        elif isinstance(subject, pynt.xmlns.RDFObject):
            if self.mayPrintConfigured():
                title = "Configuration of %s" % subject.getName()
            else:
                title = "Static information of %s" % subject.getName()
        else:
            title = "Information on %s %s" % (type(subject).__name__, subject)
        self.write('<rdfs:label xml:lang="en">%s</rdfs:label>' % self.encode(title))
        self.write('<dc:title xml:lang="en">%s</dc:title>' % self.encode(title))
        if "description" in metadata:
            self.write('<dc:description xml:lang="en">%s</dc:description>' % self.encode(metadata["description"]))
        if "publisher" in metadata:
            publisher = metadata["publisher"]
        else:
            publisher = "%s script on %s" % (pynt.output.scriptname(), socket.getfqdn())
        self.write('<dc:publisher xml:lang="en">%s</dc:publisher>' % (self.encode(publisher)))
        if "publicationdate" in metadata:
            self.write('<dcterms:issued>%s</dcterms:issued>' % (self.encode(metadata["publicationdate"])))
        else:
            self.write('<dcterms:issued>%s</dcterms:issued>' % (pynt.output.curtime()))
        self.write('<dcterms:modified>%s</dcterms:modified>' % pynt.output.curtime())
        self.indent -= 1
        self.write('</rdf:Description>')
        self.write('')
    
    def printFooter(self):
        self.indent -= 1
        self.write('</rdf:RDF>')
    
    def printRDFObjectBody(self, rdfobject):
        self.write( '<rdfs:label>' + self.encode(rdfobject.getName()) + '</rdfs:label>')
        if rdfobject.getDescription():
            self.write('<dc:description xml:lang="en">' + self.encode(rdfobject.getDescription()) + '</dc:description>')
        for (ns,pred,value) in rdfobject.getRDFProperties():
            self.write('<%s:%s>%s</%s:%s>' % (ns.prefix,pred,self.encode(value),ns.prefix,pred))
            
    def printDeviceBody(self, device):
        self.printRDFObjectBody(device)
        if device.getLocatedAt():
            self.write('<ndl:locatedAt rdf:resource="%s"/>' % device.getLocatedAt().getURIdentifier())
        for interface in device.getLogicalInterfaces(ordered=True):
            if self.mayPrintConfigured() or not interface.removable: # Print fixed interface always; removable only if mayPrintConfigured()
                self.write('<ndl:hasInterface rdf:resource="%s"/>' % interface.getURIdentifier())
        for switchmatrix in device.getSwitchMatrices():
            if self.mayPrintChildren():
                self.write('<capability:hasSwitchMatrix>')
                self.indent += 1
                self.printSwitchMatrix(switchmatrix)
                self.indent -= 1
                self.write('</capability:hasSwitchMatrix>')
            else:
                self.write('<capability:hasSwitchMatrix rdf:resource="%s"/>' % switchmatrix.getURIdentifier())
    
    def printDevice(self, device):
        self.write('<ndl:Device rdf:about="%s">' % device.getURIdentifier())
        self.indent += 1
        self.printDeviceBody(device)
        self.indent -= 1
        self.write('</ndl:Device>')
        # if self.mayPrintChildren():
        #     self.write('')
        #     for blade in device.getBlades():
        #         self.printBlade(blade)
        #     self.write('')
        #     for interface in device.getLogicalInterfaces():
        #         if self.isRoot(interface):
        #             self.printInterface(interface)
        #             self.write('')
    
    def printSwitchMatrix(self, switchmatrix):
        if switchmatrix.getDevice() and self.mayPrintChildren() and self.indent == 1:
            return
        self.write('<capability:SwitchMatrix rdf:about="%s">' % switchmatrix.getURIdentifier())
        layer = switchmatrix.getLayer()
        assert(layer != None)
        self.indent += 1
        self.write('<ndl:layer rdf:resource="%s" />' % layer.getURIdentifier())
        if switchmatrix.getSwitchingCapability():
            self.write('<capability:hasSwitchingCapability rdf:resource="%s" />' % layer.getURIdentifier())
        if switchmatrix.getSwappingCapability():
            self.write('<capability:hasSwappingCapability rdf:resource="%s" />' % layer.getURIdentifier())
        for interface in switchmatrix.getInterfaces():
            self.write('<ndl:hasInterface rdf:resource="%s"/>' % interface.getURIdentifier())
        self.indent -= 1
        self.write('</capability:SwitchMatrix>')
    
    def printBlade(self, blade):
        self.write('<physical:Blade rdf:about="' + blade.getURIdentifier() + '">')
        self.indent += 1
        self.printRDFObjectBody(blade)
        if blade.getVendorType():
            self.write('<physical:vendorEquipmentType>' + blade.getVendorType() + '</physical:vendorEquipmentType>')
        if blade.getSWVersion():
            self.write('<physical:version>' + blade.getSWVersion() + '</physical:version>')
        if blade.getAdminStatus() != None:
            status = pynt.output.boolstr(blade.getAdminStatus(), 'True', 'False')
            self.write('<physical:poweredOn>%s</physical:poweredOn>' % status)
        self.indent -= 1
        self.write('</physical:Blade>')
    
    def printInterface(self, interface):
        if interface.removable and self.staticOnly():
            return
        # Output ndl:Interface, ethernet:EthernetInterface, even though the later implies the former plus ethernet:EthernetNetworkElement
        if interface.isPotential():
            if interface.getServerInterfaces() and self.mayPrintChildren() and self.indent == 1:
                return
            interfacetype = 'capability:PotentialMuxInterface'
        else:
            interfacetype = 'ndl:Interface'
        #if interface.uri:
        #    interfacetype = interface.uri
        self.write('<%s rdf:about="%s">' % (interfacetype,interface.getURIdentifier()))
        self.indent += 1
        if interface.removable:
            self.write('<rdf:type rdf:resource="http://www.science.uva.nl/research/sne/ndl/capability#InstantiatedMuxInterface"/>')
        elif interface.configurable:
            self.write('<rdf:type rdf:resource="http://www.science.uva.nl/research/sne/ndl#ConfigurableInterface"/>')
        if interface.layer:
            self.write('<rdf:type rdf:resource="%s"/>' % (interface.layer.getURIdentifier()))
        else:
            self.write( '<!-- unspecified layer -->')
        self.printInterfaceBody(interface)
        self.printInterfaceSwitches(interface)
        self.printInterfaceChilds(interface)
        self.indent -= 1
        self.write('</%s>' % interfacetype)
    
    def printInterfaceBody(self, interface):
        # common properties
        if interface.isPotential():
            self.write( '<!-- potential %s -->' % type(interface).__name__)
            ethns = pynt.xmlns.GetNamespaceByPrefix("ethernet")
            ethlayer    = pynt.xmlns.GetRDFObject("EthernetNetworkElement",  namespace=ethns, klass=pynt.layers.Layer)
            if interface.getLabelSet() and interface.getLayer() == ethlayer:
            # port_tag.addRdfProperty(nmwgns,"vlanRangeAvailability", linkobj.vlanRangeAvailability)
                self.write('<nmwgt:vlanRangeAvailability>%s</nmwgt:vlanRangeAvailability>' % str(interface.getLabelSet())[1:-1])
        elif interface.removable:
            self.write( '<!-- instantiated %s -->' % type(interface).__name__)
        elif interface.configurable:
            self.write( '<!-- configurable %s -->' % type(interface).__name__)
        else:
            self.write( '<!-- static %s -->' % type(interface).__name__)
        self.printRDFObjectBody(interface)
        for connectedIntf in interface.getConnectedInterfacesOnly():
            self.write('<ndl:connectedTo rdf:resource="%s" />' % connectedIntf.getURIdentifier())
        for linkedIntf in interface.getLinkedInterfacesOnly():
            self.write('<ndl:linkedTo rdf:resource="%s" />' % linkedIntf.getURIdentifier())
        # print generic properties (layer is already printed earlier)
        if isinstance(interface, pynt.technologies.ip.IPInterface):
            if interface.getIPAddress():
                self.write('<ip:address>%s</ip:address>' % interface.getIPAddress())
            if hasattr(interface, "OSPFP2PInterface"):
                self.write('<rdf:type rdf:resource="http://www.science.uva.nl/research/sne/ndl/ospf#OSPFP2PInterface" />')
            if hasattr(interface, "OSPFTEP2PInterface"):
                self.write('<rdf:type rdf:resource="http://www.science.uva.nl/research/sne/ndl/ospf#OSPFTEP2PInterface" />')
        if interface.actual:
            if interface.getCapacity() != None:
                self.write('<ndl:capacity rdf:datatype="http://www.w3.org/2001/XMLSchema#float">%d</ndl:capacity> <!-- %s -->' % (interface.getCapacity(), pynt.output.humanReadable(interface.getCapacity()*8, 'bit/s')))
            if self.mayPrintConfigured() and (not interface.actual) and (interface.getEgressBandwidth() != None):
                self.write('<ndl:egressBandwidth>%s</ndl:egressBandwidth>' % (interface.getEgressBandwidth()))
            if self.mayPrintConfigured() and (not interface.actual) and (interface.getIngressBandwidth() != None):
                self.write('<ndl:ingressBandwidth>%s</ndl:ingressBandwidth>' % (interface.getIngressBandwidth()))
        
        layeruri = None
        layer = interface.getLayer()
        if layer:
            layeruri = layer.getURIdentifier()
            self.write('<ndl:layer rdf:resource="%s" />' % layeruri)
        # Layer specific properties
        if   layeruri == "http://www.science.uva.nl/research/sne/ndl/ip#IPNetworkElement":
            self.printIPInterfaceProperties(interface)
        elif layeruri == "http://www.science.uva.nl/research/sne/ndl/ethernet#EthernetNetworkElement":
            self.printEthernetInterfaceProperties(interface)
        elif layeruri == "http://www.science.uva.nl/research/sne/ndl/wdm#LambdaNetworkElement":
            self.printLambdaInterfaceProperties(interface)
        elif layeruri == "http://www.science.uva.nl/research/sne/ndl/wdm#FiberNetworkElement":
            self.printFiberInterfaceProperties(interface)
        elif layeruri == "http://www.science.uva.nl/research/sne/ndl/copper#TwistedPairNetworkElement":
            self.printTwistedPairInterfaceProperties(interface)
        elif layeruri == "http://www.science.uva.nl/research/sne/ndl/tdm#OC192NetworkElement":
            self.printOCInterfaceProperties(interface)
        else:
            pass
            #self.printDefaultInterfaceProperties(interface)
    
    def printIPInterfaceProperties(self, interface):
        if not isinstance(interface, pynt.technologies.ip.IPInterface):
            return
        if interface.getMetric():
            self.write('<ip:metric rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">%d</ip:metric>' % interface.getMetric())
    
    def printEthernetInterfaceProperties(self, interface):
        if not isinstance(interface, pynt.technologies.ethernet.EthernetInterface):
            return
        if self.staticOnly():
            return
        # everything hereafter is dynamic information
        if interface.getUntaggedVLANid() != None:
            self.write('<ethernet:VLAN rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">%d</ethernet:VLAN>' % (interface.getUntaggedVLANid()))
        if interface.getEgressLabel() != None:
            self.write('<ethernet:IEEE802-1Q rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">' \
                    '%d</ethernet:IEEE802-1Q>' % (interface.getEgressLabel()))
        if interface.getAdminStatus() != None:
            status1 = pynt.output.boolstr(interface.getAdminStatus(), 'up', 'down')
            status2 = pynt.output.boolstr(interface.getAdminStatus(), 'light is', 'no light')
            self.write('<ethernet:egressStatus>%s</ethernet:egressStatus> <!-- %s sent out -->' % (status1, status2))
        if interface.getLinkStatus() != None:
            status1 = pynt.output.boolstr(interface.getLinkStatus(), 'up', 'down')
            status2 = pynt.output.boolstr(interface.getLinkStatus(), 'light is', 'no light')
            self.write('<ethernet:ingressStatus>%s</ethernet:ingressStatus> <!-- %s received -->' % (status1, status2))
        if interface.getMTU() != None:
            self.write('<ethernet:MTU rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">%d</ethernet:MTU> <!-- max payload is %d bytes -->' % (interface.getMTU(), interface.getMTU()-18))
        # TODO: Add these parameters
        # <ethernet:frameSizeRange rdf:resource="http://www.science.uva.nl/research/sne/ndl/ethernet#FrameSize:576"/>
        # <ethernet:frameSizeRange rdf:resource="http://www.science.uva.nl/research/sne/ndl/ethernet#FrameSize:1500"/>
        # <ethernet:frameSizeRange rdf:resource="http://www.science.uva.nl/research/sne/ndl/ethernet#FrameSize:9000"/>
    
    def printLambdaInterfaceProperties(self, interface):
        if not isinstance(interface, pynt.technologies.wdm.LambdaInterface):
            return
        if interface.getWavelenght():
            self.write('<wdm:wavelength rdf:datatype="http://www.w3.org/2001/XMLSchema#float">%d</wdm:wavelength>' % (interface.getWavelenght()))
    
    def printFiberInterfaceProperties(self, interface):
        if not isinstance(interface, pynt.technologies.wdm.FiberInterface):
            return
        if interface.getIngressPowerLevel():
            self.write('<wdm:ingressPowerLevel rdf:datatype="http://www.w3.org/2001/XMLSchema#float">%0.2f</wdm:ingressPowerLevel>' % (interface.getIngressPowerLevel()))
        if interface.getEgressPowerLevel():
            self.write('<wdm:egressPowerLevel rdf:datatype="http://www.w3.org/2001/XMLSchema#float">%0.2f</wdm:egressPowerLevel>' % (interface.getEgressPowerLevel()))
        if interface.getSpacing():
            self.write('<wdm:spacing rdf:resource="%s"/>' % (interface.getSpacingURI()))
        if interface.getCladding():
            self.write('<wdm:cladding rdf:resource="%s"/>' % (interface.getCladdingURI()))
        if interface.getPolish():
            self.write('<wdm:polish rdf:resource="%s"/>' % (interface.getPolishURI()))
        if interface.getConnector():
            self.write('<wdm:transceiver rdf:resource="%s"/>' % (interface.getTransceiverURI()))
        if interface.getTransceiver():
            self.write('<wdm:connector rdf:resource="%s"/>' % (interface.getConnectorURI()))
    
    def printTwistedPairInterfaceProperties(self, interface):
        pass
    
    def printOCInterfaceProperties(self, interface):
        if not isinstance(interface, pynt.technologies.tdm.OC192Interface):
            return
        pass
    
    def printInterfaceSwitches(self, interface):
        if self.staticOnly():
            return
        for switchinterface in interface.getActualSwitchedInterfaces():
            self.write('<ndl:switchedTo rdf:resource="%s"/>' % switchinterface.getURIdentifier())
        for switchinterface in interface.getPacketSwitchedInterfaces():
            self.write('<ndl:packetSwitchedTo rdf:resource="%s"/>' % switchinterface.getURIdentifier())
    
    def isRoot(self, interface):
        return len(interface.getAllServerTuples()) != 1
    
    def printInterfaceChilds(self, interface):
        for (clientinterface,adaptationfunction) in interface.getAllClientTuples():
            if clientinterface.removable and self.staticOnly():
                continue
            elif (not self.mayPrintChildren()) or self.isRoot(clientinterface):
                self.printInterfacePointer(adaptationfunction, clientinterface)
            else:
                self.printChildInterface(adaptationfunction, clientinterface)
        # adaptation = interface.getExternalClientAdaptation()
        # for clientinterface in interface.getExternalClientInterfaces():
        #     if clientinterface.isConfigured() and self.staticOnly():
        #         continue
        #     self.printInterfacePointer(adaptation, clientinterface)
    
    def printInterfacePointer(self, adaptation, interface):
        self.write('<' + str(adaptation.getIdentifier()) + ' rdf:resource="' + interface.getURIdentifier() + '"/>')
    
    def printChildInterface(self, adaptation, interface):
        self.write('<' + str(adaptation.getXMLEltIdentifier()) + '>')
        self.indent += 1
        self.printInterface(interface)
        self.indent -= 1
        self.write('</' + str(adaptation.getXMLEltIdentifier()) + '>')

    def printBroadcastSegment(self, bc):
        self.write('<ndl:BroadcastSegment rdf:about="%s" >' % bc.getURIdentifier())
        self.indent += 1
        for intf in bc.getConnectedInterfaces():
            self.write('<ndl:connectedTo rdf:resource="%s" />' % intf.getURIdentifier())
        self.indent -= 1
        self.write('</ndl:BroadcastSegment>')
    
    def printLink(self, link):
        self.write('<ndl:Link rdf:about="%s" >' % link.getURIdentifier())
        self.indent += 1
        for intf in link.getConnectedInterfaces():
            self.write('<ndl:connectedTo rdf:resource="%s" />' % intf.getURIdentifier())
        self.indent -= 1
        self.write('</ndl:Link>')

    def printLocation(self, loc):
        self.write('<ndl:Location rdf:about="%s">' % loc.getURIdentifier())
        self.indent += 1
        self.printRDFObjectBody(loc)
        self.indent -= 1
        self.write('</ndl:Location>')
    
    def printAdminDomain(self, dom):
        self.write('<ndl:AdminDomain rdf:about="%s">' % dom.getURIdentifier())
        self.indent += 1
        self.printRDFObjectBody(dom)
        self.indent -= 1
        self.write('</ndl:AdminDomain>')
        

# TODO: debug: RDFv22 prints identifiers like "Force10:te6/0:vlan9:vlan9".
# also, the indent is not always right


class RDFv22Output(pynt.output.BaseOutput):
    

    """manually formatted RDF"""
    devnamespace = '#'
    intfnamespace = '#Device:'
    
    def interfaceIdentifier(self, interface):
        return self.intfnamespace + interface.getIdentifier()
    
    def channelIdentifier(self, interface, vlanid):
        return self.intfnamespace + pynt.elements.InterfaceIdentifier(interface.getPrefix(), interface.getBlade(), interface.getPort()) + ":" + pynt.technologies.ethernet.VlanIdentifier(vlanid)
    
    def printDevice(self,device):        
        """print rdf headers and force10 static information, using NDL multilayer v 2.2 format (obsolete)"""
        if isinstance(device, pynt.technologies.ethernet.EthernetDevice):
            self.printEthernetDevice(device)
        elif isinstance(device, pynt.technologies.wdm.OXCDevice):
            self.printFiberDevice(device)
        else:
            TypeError("device is not of type EthernetDevice or FiberDevice")
    
    def printEthernetDevice(self,device):
        
        """print rdf headers and force10 static information, using NDL multilayer v 2.2 format (obsolete)"""
        self.intfnamespace = "#"+device.getIdentifier()+":"
        # self.intfnamespace = device.getNamespace().getURI()
        self.write('<?xml version="1.0" encoding="UTF-8"?>')
        self.write('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        self.write('         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
        self.write('         xmlns:xsd="http://www.w3.org/2001/XMLSchema#"')
        self.write('         xmlns:ndl="http://www.science.uva.nl/research/sne/ndl#"')
        self.write('         xmlns:ndlml="http://www.science.uva.nl/research/sne/ndlml#"')
        self.write('>')
        self.write('')
        self.write('<!-- ')
        self.write('    WARNING: This file is in NDL 2.2 format, which was an experimental format. ')
        self.write('    Please use a newer file format (version 2.4)!!!')
        self.write('-->')
        self.write('')
        self.write('<ndl:Location rdf:about="#Lighthouse">')
        self.write('    <rdfs:label>Lighthouse</rdfs:label>')
        self.write('</ndl:Location>')
        self.write('')
        self.write('<!--')
        self.write('    Below general Ethernet definitions are given.')
        self.write('-->')
        self.write('')
        self.write('<ndlml:Layer rdf:about="#Ethernet">')
        self.write('    <ndlml:hasLabelType>')
        self.write('        <ndlml:LabelType rdf:about="#802.1q">')
        self.write('            <ndlml:hasLabelRange>')
        self.write('                <rdf:Bag>')
        self.write('                    <rdf:_1>')
        self.write('                        <ndlml:range>')
        self.write('                            <xsd:minInclusive rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">0</xsd:minInclusive>')
        self.write('                            <xsd:maxInclusive rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">4095</xsd:maxInclusive>')
        self.write('                        </ndlml:range>')
        self.write('                    </rdf:_1>')
        self.write('                </rdf:Bag>')
        self.write('            </ndlml:hasLabelRange>')
        self.write('        </ndlml:LabelType>')
        self.write('    </ndlml:hasLabelType>')
        self.write('    <ndlml:hasLabelType>')
        self.write('        <ndlml:LabelType rdf:about="#MACaddress"/>')
        self.write('    </ndlml:hasLabelType>')
        self.write('    <ndlml:hasPropertyType>')
        self.write('        <ndlml:PropertyType rdf:about="#tagging">')
        self.write('            <ndlml:hasPropertyValue>')
        self.write('                <rdf:Alt>')
        self.write('                    <rdf:_1>')
        self.write('                        <ndlml:LabelValue rdf:about="#untagged"/>')
        self.write('                    </rdf:_1>')
        self.write('                    <rdf:_2>')
        self.write('                        <ndlml:LabelValue rdf:about="#tagged"/>')
        self.write('                    </rdf:_2>')
        self.write('                    <rdf:_3>')
        self.write('                        <ndlml:LabelValue rdf:about="#Q-in-Q"/>')
        self.write('                    </rdf:_3>')
        self.write('                </rdf:Alt>')
        self.write('            </ndlml:hasPropertyValue>')
        self.write('        </ndlml:PropertyType>')
        self.write('    </ndlml:hasPropertyType>')
        self.write('</ndlml:Layer>')
        self.write('')
        # print shortcuts for the definitiion of all VLAN tags used
        self.write('<!--')
        self.write('    Next up are shortcut definitions for VLAN tags used.')
        self.write('-->')
        self.write('')
        for vlan in device.getVlans():
            self.write('<ndlml:Label rdf:about="#vlan' + str(vlan.getVlanId()) + '">')
            self.write('    <rdf:value rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">' + str(vlan.getVlanId()) + '</rdf:value>')
            self.write('    <rdf:type rdf:resource="#802.1q"/>')
            self.write('</ndlml:Label>')
        self.write('')
        self.write('<!--')
        self.write('    So far, the common part (which typically would be defined in a common RDF file).')
        self.write('    Now, the definition of the interfaces in the Force10, starting with the device,')
        self.write('    noting it is an Ethernetswitch, switching data based on 802.1q labels.')
        self.write('    The device can only switch, not swap. So VLAN 30 of interface A can\'t be connected ')
        self.write('    to VLAN 31 of interface B since (30 != 31).')
        self.write('    Note that there are TWO switchedTo statements for channels with VLAN 30. This ')
        self.write('    is because each interface in that VLAN will forward the data to TWO interfaces.')
        self.write('-->')
        self.write('')
        self.write('<ndl:Device rdf:about="' + self.devnamespace + device.getIdentifier() + '">')
        self.write('    <rdfs:label>' + device.getName() + '</rdfs:label>')
        self.write('    <ndl:locatedAt rdf:resource="#Lighthouse"/>')
        for interface in device.getNativeInterfaces():
            self.write('    <ndl:hasInterface rdf:resource="' + self.interfaceIdentifier(interface) + '"/>')
        self.write('    <ndlml:hasSwitchingCapability rdf:resource="#802.1q"/>')
        self.write('</ndl:Device>')
        self.write('')
        
        for interface in device.getNativeInterfaces():
            untagged = 0
            tagged = 0
            printedtag = 0
            
            self.write('<ndl:Interface rdf:about="' + self.interfaceIdentifier(interface) + '">')
            self.write('    <rdfs:label>' + 'Force10:' + interface.getName() + '</rdfs:label>')
            if None != interface.getAdminStatus():
                self.write('    <ndlml:adminStatus>'+ interface.getAdminStatus() +'</ndlml:adminStatus>')
            if None != interface.getLinkStatus():
                self.write('    <ndlml:linkStatus>'+ interface.getLinkStatus() +'</ndlml:linkStatus>')
            
            untaggedvlan = interface.getUntaggedVLANid()
            if None != untaggedvlan:
                self.write('    <ndlml:hasProperty rdf:resource="#untagged"/>')
                self.write('    <ndlml:hasChannel>')
                self.write('        <ndlml:Channel rdf:about="' + self.channelIdentifier(interface, untaggedvlan) + '">')
                self.write('            <ndlml:hasLabel rdf:datatype="#802.1q"></ndlml:hasLabel>')
                for switchinterface in interface.getActualSwitchedInterfaces():
                    self.write('            <ndl:switchedTo rdf:resource="%s"/>' % (self.channelIdentifier(interface, untaggedvlan)))
                    # self.write('            <ndl:switchedTo rdf:resource="%s"/>' % switchinterface.getURIdentifier())
                for switchinterface in interface.getPacketSwitchedInterfaces():
                    self.write('            <ndl:switchedTo rdf:resource="%s"/>' % (self.channelIdentifier(interface, untaggedvlan)))
                    # self.write('            <ndl:switchedTo rdf:resource="%s"/>' % switchinterface.getURIdentifier())
                self.write('        </ndlml:Channel>')
                self.write('    </ndlml:hasChannel>')
            
            taggedvlans = interface.getTaggedVLANids()
            if None != taggedvlans:
                self.write('    <ndlml:hasProperty rdf:resource="#tagged"/>')
                for vlanid in taggedvlans:
                    self.write('    <ndlml:hasChannel>')
                    self.write('        <ndlml:Channel rdf:about="' + self.channelIdentifier(interface, untaggedvlan) + '">')
                    self.write('            <ndlml:hasLabel rdf:datatype="#802.1q">' + str(vlanid) + '</ndlml:hasLabel>')
                    for switchinterface in interface.getActualSwitchedInterfaces():
                        self.write('           <ndl:switchedTo rdf:resource="%s"/>' % (self.channelIdentifier(interface, untaggedvlan)))
                        # self.write('           <ndl:switchedTo rdf:resource="%s"/>' % switchinterface.getURIdentifier())
                    for switchinterface in interface.getPacketSwitchedInterfaces():
                        self.write('           <ndl:switchedTo rdf:resource="%s"/>' % (self.channelIdentifier(interface, untaggedvlan)))
                        # self.write('           <ndl:switchedTo rdf:resource="%s"/>' % switchinterface.getURIdentifier())
                    self.write('        </ndlml:Channel>')
                    self.write('    </ndlml:hasChannel>')
            
            self.write('</ndl:Interface>')
        
        self.write('</rdf:RDF>')
    
    def printFiberDevice(self,device):
        """print rdf headers and force10 static information, using NDL multilayer v 2.2 format (obsolete)"""
        self.intfnamespace = "#"+device.getIdentifier()+":"
        # self.intfnamespace = device.getNamespace().getURI()
        # print rdf headers and glimmerglass static information:
        self.write('<?xml version="1.0" encoding="UTF-8"?>')
        self.write('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        self.write('         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
        self.write('         xmlns:xsd="http://www.w3.org/2001/XMLSchema#"')
        self.write('         xmlns:dc="http://purl.org/dc/elements/1.1/"')
        self.write('         xmlns:ndl="http://www.science.uva.nl/research/sne/ndl#"')
        self.write('         xmlns:ndlml="http://www.science.uva.nl/research/sne/ndlml#"')
        self.write('         xmlns:ndlphy="http://www.science.uva.nl/research/sne/ndl/physical#"')
        self.write('>')
        self.write('')
        self.write('<ndl:Device rdf:about="%s">' % device.getURIdentifier())
        self.write('    <rdfs:Label xml:lang="en-US">%s</rdfs:Label>' % device.getName())
        self.write('    <dc:description xml:lang="en-US">%s</dc:description>' % device.getDescription())
        for interface in device.getNativeInterfaces():
            url = '%s%s:%s' % (interface.namespace.getURI(), device.getIdentifier(), interface.getPort());
            self.write('    <ndl:hasInterface rdf:resource="'+url+'"/>')
        self.write('    <ndlml:hasSwitchingCapability rdf:resource="#Interface"/>')
        self.write('</ndl:Device>')
        self.write('')
        
        for interface in device.getNativeInterfaces():
            srcurl = '%s%s:%s' % (interface.namespace.getURI(), device.getIdentifier(), interface.getPort());
            self.write('<ndl:Interface rdf:about="'+srcurl+'">')
            self.write('    <rdfs:Label>%s</rdfs:Label>' % interface.getName())
            if interface.getDescription():
                self.write('    <dc:description>'+ interface.getDescription() +'</dc:description>')
            if interface.getIngressPowerLevel():
                self.write('    <ndlphy:inpowerlevel>%0.3f</ndlphy:inpowerlevel>' % interface.getIngressPowerLevel())
            if interface.getEgressPowerLevel():
                self.write('    <ndlphy:outpowerlevel>%0.3f</ndlphy:outpowerlevel>' % interface.getEgressPowerLevel())
            for switchinterface in interface.getActualSwitchedInterfaces():
                desturl = '%s%s:%s' % (interface.namespace.getURI(), device.getIdentifier(), interface.getPort());
                self.write('    <ndl:switchedTo rdf:resource="'+desturl+'"/>')
            self.write('</ndl:Interface>')
        
        self.write('')
        self.write('</rdf:RDF>')


