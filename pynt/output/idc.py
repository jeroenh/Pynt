import time
# import xml.etree.ElementTree as ET
import lxml.etree as ET
import pynt.output

nmwgns      = pynt.xmlns.GetCreateWellKnownNamespace("nmwgt")

class IDCTopoOutput(pynt.output.BaseOutput):
    def __init__(self, outfile=None, subject=None, atomic=True):
        pynt.output.BaseOutput.__init__(self,outfile=outfile,subject=subject)
        self.domain = None
    
    def printHeader(self):
        self.top = ET.Element("topology", xmlns="http://ogf.org/schema/network/topology/ctrlPlane/20080828/", id="rdf-generator-%s" % time.strftime("%Y%m%d%H%M"))
    
    def printFooter(self):
        # print ET.tostring(self.top,pretty_print="True")
        self.write( ET.tostring(self.top,pretty_print="True"))
    
    def printAdminDomain(self, dom):
        if self.domain is None:
            idc = ET.SubElement(self.top,"idcId")
            idc.text = "foobar"
            if dom:
                identifier = dom.getURIdentifier()
            else:
                identifier = "urn:ogf:network:domain=ndl-generated"
            self.domain = ET.SubElement(self.top,"domain", id=identifier)
        else:
            #Domain is already printed, so nothing to do here.
            pass
    
    def printDevice(self, device):
        if self.domain is None:
            self.printAdminDomain(device.getDomain())
        self.node = ET.SubElement(self.domain,"node", id=device.getURIdentifier())
        # TODO: Fetch address
        for intf in device.getLogicalInterfaces():
            clients = intf.getPotentialClientTuples()
            if clients:
                intfEl = ET.SubElement(self.node,"port",id=intf.getURIdentifier())
                if intf.getCapacity() is not None:
                    el = ET.SubElement(intfEl,"capacity")
                    el.text = str(int(intf.getCapacity()))
                if intf.getMaximumReservableCapacity() is not None:
                    el = ET.SubElement(intfEl,"maximumReservableCapacity")
                    el.text = str(int(intf.getMaximumReservableCapacity()))
                if intf.getMinimumReservableCapacity() is not None:
                    el = ET.SubElement(intfEl,"minimumReservableCapacity")
                    el.text = str(int(intf.getMinimumReservableCapacity()))
                if intf.getGranularity() is not None:
                    el = ET.SubElement(intfEl,"granularity")
                    el.text = str(int(intf.getGranularity()))
                for (link,adap) in clients:
                    linkEl = ET.SubElement(intfEl,"link",id=link.getURIdentifier())
                    if intf.getConnectedInterfaces():
                        el = ET.SubElement(linkEl,"remoteLinkId")
                        el.text = intf.getConnectedInterfaces()[0].getURIdentifier()
                    if link.getMetric() is not None:
                        el = ET.SubElement(linkEl,"trafficEngineeringMetric")
                        el.text = str(int(link.getMetric()))
                    if link.getCapacity() is not None:
                        el = ET.SubElement(linkEl,"capacity")
                        el.text = str(int(link.getCapacity()))
                    if link.getMaximumReservableCapacity() is not None:
                        el = ET.SubElement(linkEl,"maximumReservableCapacity")
                        el.text = str(int(link.getMaximumReservableCapacity()))
                    if link.getMinimumReservableCapacity() is not None:
                        el = ET.SubElement(linkEl,"minimumReservableCapacity")
                        el.text = str(int(link.getMinimumReservableCapacity()))
                    if link.getGranularity() is not None:
                        el = ET.SubElement(linkEl,"granularity")
                        el.text = str(int(link.getGranularity()))
                    if adap == pynt.xmlns.GetRDFObject("Tagged-Ethernet", pynt.xmlns.GetNamespaceByPrefix("ethernet"), klass=pynt.layers.AdaptationFunction):
                        iscd = ET.SubElement(linkEl,"SwitchingCapabilityDescriptors")
                        capType = ET.SubElement(iscd,"switchingcapType")
                        capType.text = "l2sc"
                        encType = ET.SubElement(iscd,"encodingType")
                        encType.text = "ethernet"
                        iscdSpec = ET.SubElement(iscd,"switchingCapabilitySpecificInfo")
                        if intf.hasRDFProperty(nmwgns,"mtu"):
                            mtu = ET.SubElement(iscdSpec,"interfaceMTU")
                            mtu.text = str(int(intf.getRDFProperty(nmwgns,"mtu")))
                        vlan = ET.SubElement(iscdSpec,"vlanRangeAvailability")
                        vlan.text = str(link.getLabelSet())[1:-1]
                    
                

    def printBroadcastSegment(self, bc):
        pass
        
    def printInterface(self, interface):
        pass
            
    def printLocation(self, loc):
        pass

        
    
# topology
#   domain
#     node (address)
#       port (capacity, max, min, granularity)
#         link (capacity, miin, max, granularity, teMetric)
#           SCD (swcaptype, encType, swcSpecificInfo)