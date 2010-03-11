# -*- coding: utf-8 -*-
"Output module to VNE Configuration format, in order to create Network Emulations, see http://ndl.uva.netherlight.nl/trac/vne/"

import xml.dom.minidom
import types
import IPy
import sys

import pynt.output
import pynt.technologies.ip

class VNEConfigOutput(pynt.output.BaseOutput):
    
    def __init__(self, outfile=None, subject=None, atomic=True):
        pynt.output.BaseOutput.__init__(self, outfile, subject, atomic)
        self.xmldoc = xml.dom.minidom.Document()
        self.rootElement         = self._newChild(self.xmldoc,      "config")
        self.devicesElement      = self._newChild(self.rootElement, "devices")
        self.connectionsElement  = self._newChild(self.rootElement, "connections")
        self.connections         = []
        self.tunnels             = []
        self.interfaceDict       = {}
        self.controlPlaneSwitch  = self._newChild(self.devicesElement, "switch", name="switch1") 
        self.controlPlaneSwitchCounter = 0
        self.greCounter = 0

    def _newChild(self, parent, childName, **attributes):
        "Helper function to easily create childtags with attributes"
        # self.logger.debug("%s is getting a new child %s (%s)" % (parent.localName, childName, attributes))
        child = self.xmldoc.createElement(childName)
        for name,value in attributes.iteritems():
            child.setAttribute(name, value)
        parent.appendChild(child)
        return child
    
    def addControlPlaneConnection(self, device, interface):
        self._newChild(self.controlPlaneSwitch, "interface", name="eth%s"%self.controlPlaneSwitchCounter, bridge="br0")
        con = self._newChild(self.connectionsElement, "connection")
        self._newChild(con, "device", name="switch1", interface="eth%s"%self.controlPlaneSwitchCounter)
        self._newChild(con, "device", name=device, interface=interface)
        self.controlPlaneSwitchCounter += 1

    def setOutputFile(self, outfile):
        # In this module we only write output at the very end.
        if outfile == None:
            outfile = sys.stdout
        if (outfile == self.outfile) or (outfile == self.filename):
            return
        if self.outfile:
            self.closefile()
        if isinstance(outfile, types.FileType):
            self.outfile = outfile
        elif isinstance(outfile, types.StringTypes): 
            self.filename = outfile
            self.openfile(append=False)
        else:
            raise AttributeError("output parameter for BaseOutput.setOutput() must be a FileType or filename")
            self.outfile = sys.stdout

    def closefile(self):
        if self.filename:
            self.outfile = open(self.filename,'w')
            self.outfile.write(self.xmldoc.toprettyxml())
            self.outfile.close()
        else:
            print self.xmldoc.toprettyxml()
        self.outfile = None
    
    def saveNarb(self, device):
        # Save the narb device and print it at the last moment.
        self.__narb = device
        
    def printNarb(self, device):
        devTag = self._newChild(self.devicesElement, "host", name=device.getName())
        interfaceTag = self._newChild(devTag, "interface", name="eth0", loopback="True")
        narbControlIp = device.getName()[3:]
        self._newChild(interfaceTag, "ipv4", addr=narbControlIp)
        self.addControlPlaneConnection(device.getName(), "eth0")
        tunnelDest = device.getLogicalInterfaces()[0].getConnectedInterfaces()[0]
        greid = self.createGreTunnel((device.getLogicalInterfaces()[0], None), (tunnelDest, None))
        # We have to add a narbintra stanza to the receiving end as well
        tunnelDestName = tunnelDest.getDevice().getName()
        for dev in self.xmldoc.getElementsByTagName("host"):
            if dev.getAttribute("name") == tunnelDestName:
                dev.getElementsByTagName("dragon")[0].setAttribute("narbintra","gre%s"%greid)
        # Add the narb to all the devices so that they can find it.
        for dtag in self.xmldoc.getElementsByTagName("dragon"):
            dtag.setAttribute("narb",narbControlIp)
        # Finally we add our own dragon tag, so we don't get the narb statement
        # We calculate the narb domain in a somewhat hackish way, we take the /16 from the controlplane
        # address, and get the network address from that.
        # TODO: fixed 16 subnet?
        narbNet = unicode(IPy.IP(narbControlIp).make_net("255.255.0.0").net())
        self._newChild(devTag, "dragon", role="narb", narbdomain=narbNet, narbintra="gre%s"%greid)

    
    def printDevice(self, device):
        """subfunction of output. Assumes that the fileobject is open. Do not call directly, but use output()"""
        #Filter out the Narb:
        if len(device.getLogicalInterfaces()) == 1 and hasattr(device.getLogicalInterfaces()[0], "OSPFP2PInterface"):
            self.saveNarb(device)
        else:
            devTag = self._newChild(self.devicesElement, "host", name=device.getName())
            self._newChild(devTag, "dragon", role="vlsr")
            ifCounter = 0
            for interface in device.getLogicalInterfaces():
                if hasattr(interface, "OSPFP2PInterface"):
                    continue
                # if hasattr(interface, "OSPFTEP2PInterface"):
                #     continue
                if interface.getName() in device.getName():
                    # The primary interface in OSPF determines the name of the device
                    interfaceTag = self._newChild(devTag, "interface", name="eth0", loopback="True")
                    self.interfaceDict[interface] = (device.getName(),"eth0")
                    self.addControlPlaneConnection(device.getName(), "eth0")
                else:
                    ifCounter += 1
                    interfaceTag = self._newChild(devTag, "interface", name="eth%s" % ifCounter)
                    self.interfaceDict[interface] = (device.getName(),"eth%s" % ifCounter)
                if isinstance(interface, pynt.technologies.ip.IPInterface) and interface.getIPAddress() \
                    and not hasattr(interface, "OSPFTEP2PInterface"):
                    self._newChild(interfaceTag, "ipv4", addr=interface.getIPAddress())
        
    def printInterface(self, interface):
        """subfunction of output. Assumes that the fileobject is open. Do not call directly, but use output()"""
        for connectedIntf in interface.getConnectedInterfaces():
            if hasattr(interface, "OSPFP2PInterface"):
                continue
            elif hasattr(interface, "OSPFTEP2PInterface"):
                localInterfaces = interface.getDevice().getLogicalInterfaces()
                remoteInterface = interface.getConnectedInterfaces()[0]
                remoteInterfaces = remoteInterface.getDevice().getLogicalInterfaces()
                for baseIntf in localInterfaces:
                    if not baseIntf.getConnectedInterfaces():
                        continue
                    remoteBaseIntf = baseIntf.getConnectedInterfaces()[0]
                    if remoteBaseIntf in remoteInterfaces and \
                      hasattr(remoteBaseIntf, "OSPFP2PInterface") and \
                      ((remoteBaseIntf, remoteInterface),(baseIntf, interface)) not in self.tunnels:
                        self.tunnels.append(((baseIntf, interface), (remoteBaseIntf, remoteInterface)))
            if (connectedIntf, interface) not in self.connections:
                self.connections.append((interface, connectedIntf))
                
    def printFooter(self):
        """Print footer lines."""
        self.printNarb(self.__narb)
        for intfpair in self.connections:
            con = self._newChild(self.connectionsElement, "connection")
            for intf in intfpair:
                device, intfname = self.interfaceDict[intf]
                self._newChild(con, "device", name=device, interface=intfname)
        for local,remote in self.tunnels:
            self.createGreTunnel(local,remote)

    def createGreTunnel(self, (baseIntf, interface), (remoteBaseIntf, remoteInterface)):
            self.greCounter += 1
            localIP = IPy.IP(baseIntf.getIPAddress())
            remoteIP = IPy.IP(remoteBaseIntf.getIPAddress())
            mask = localIP.make_net("255.255.255.252")
            if interface and interface.getIPAddress():
                temask = (IPy.IP(interface.getIPAddress()).make_net("255.255.255.252"))
                tun = self._newChild(self.connectionsElement, "gretunnel", name="gre%s" % self.greCounter,mask=unicode(mask), temask=unicode(temask))
                if localIP < remoteIP: # Ordering determines the ip addresses in VNE.
                    # TODO: we assume that control plane is connected through eth0.
                    self._newChild(tun, "device", name=remoteBaseIntf.getDevice().getName(), interface="eth0", \
                                    switchport=self.interfaceDict[remoteInterface][1])
                    self._newChild(tun, "device", name=baseIntf.getDevice().getName(), interface="eth0", \
                                    switchport=self.interfaceDict[interface][1])
                else:
                    self._newChild(tun, "device", name=baseIntf.getDevice().getName(), interface="eth0", \
                                    switchport=self.interfaceDict[interface][1])
                    self._newChild(tun, "device", name=remoteBaseIntf.getDevice().getName(), interface="eth0", \
                                    switchport=self.interfaceDict[remoteInterface][1])
            else:
                tun = self._newChild(self.connectionsElement, "gretunnel", name="gre%s" % self.greCounter,mask=unicode(mask))
                if localIP < remoteIP: # Ordering determines the ip addresses in VNE.
                    # TODO: we assume that control plane is connected through eth0.
                    self._newChild(tun, "device", name=remoteBaseIntf.getDevice().getName(), interface="eth0")
                    self._newChild(tun, "device", name=baseIntf.getDevice().getName(), interface="eth0")
                else:
                    self._newChild(tun, "device", name=baseIntf.getDevice().getName(), interface="eth0")
                    self._newChild(tun, "device", name=remoteBaseIntf.getDevice().getName(), interface="eth0")
            return self.greCounter
                
                

    def openfile(self, append=False):
        # In this module we only write output at the very end.
        pass
    def printDocumentMetaData(self, subject):       pass
    def printBroadcastSegment(self, bc):            pass        
    def printAdminDomain(self, dom):                pass        
    def printHeader(self):                          pass
    def printLocation(self, loc):                   pass
    def printSubject(self, subject):                pass
    def printSwitchMatrix(self, switchmatrix):      pass