# -*- coding: utf-8 -*-

# builtin modules
import os.path
import logging
# local modules
import pynt.input
import pynt.protocols.cli
import pynt.elements
import pynt.xmlns

import pynt.technologies.ethernet     # defines FiberInterface class

class PassportFetcher(pynt.input.BaseDeviceFetcher):
    """Fetches information from a Nortel passport Ethernet switch"""
    quitCmd         = 'quit'
    def __init__(self, *args, **params):
        pynt.input.BaseDeviceFetcher.__init__(self, *args, **params)
        self.subjectClass    = pynt.technologies.ethernet.EthernetDevice
    
    def setSourceHost(self, hostname, port=None):
        self.io = pynt.protocols.cli.TelnetInput(hostname=hostname, port=port)
        # self.io = pynt.protocols.cli.SSHInput(hostname=hostname, port=port)
        self.io.setDefaultTimeout(30)
        #self.io.hasecho = True
        identifier = hostname.split(".")[0]
        self.io.setPrompt(identifier.capitalize()+":[0-9]>")
    
    def setSourceFile(self, filename, hostname=None):
        self.io = pynt.protocols.cli.CLIEmulatorInput(filename=filename)
        if hostname:
            identifier = hostname.split(".")[0]
        else:
            identifier = os.path.basename(filename)
        self.io.setPrompt(identifier.capitalize()+":[0-9]>") # e.g. Nortel:5>
    
    def command(self, command, skipStartLines=0, lastSkipLineRe=None, skipEndLines=0):
        resultLines = self.io.command(command)
        return pynt.protocols.cli.ParseCLILines(resultLines, skipStartLines=skipStartLines, lastSkipLineRe=lastSkipLineRe, skipEndLines=skipEndLines)
    
    def retrieve(self):
        # get information from device
        self.io.setDefaultTimeOut(60)
        self.io.command("config cli more false")   # turn off interactive shell
        # Note that the output of this command gives a spurious prompt due to the way this is implemented.
        # Since we ignore it, this is no big issue, but you may want to be forgiving when parsing previous 
        # or commands just before or just after the "config cli more false" command.
        vlanlines      = self.command('show ports info vlans', skipStartLines=7, lastSkipLineRe=80*"-")
        interfacelines = self.command('show ports info interface', skipStartLines=8, lastSkipLineRe=80*"-")
        
        self.parseInterfaces(interfacelines)    # sets subject.interfaces
        self.parseVlans(vlanlines)

        # TODO: I don't think the vlans need to be parsed; interfacelines gives enough information
        #self.parseVlans(vlanlines)              # sets subject.vlans
        ##self.addLogicalInterfacePerBlade()
        ##self.addLogicalMACInterfaces()
        #self.parseInterfaceDetails(interfacedetails)

    def parseInterfaces(self, interfacelines):
        """Parses the interface strings and creates interface objects"""
        for line in interfacelines:
            self.parseInterfaceLine(line)
        return len(interfacelines)

    def parseInterfaceLine(self, interfaceString):
        """Parses one interface line and creates native and logical interface objects, adding proper
           adaptations to the logical interfaces."""
        splitString = interfaceString.split()
        num_elements = len(splitString)
        if num_elements != 9: # Not a valid interface line
            return
        identifier  = splitString[0] # blade/port format
        #index       = splitString[1]
        description = splitString[2] # "10GbLR" or "10GbLW" for LAN resp WAN PHY
        #linktrap    = splitString[3]
        #portlock    = splitString[4]
        mtu         = splitString[5] # MTU size
        macaddress  = splitString[6] # Physical interface address (Ethernet layer)
        adminstatus = splitString[7] # Adminstatus
        linkstatus  = splitString[8] # Operational status

        interface = self.subject.getCreateNativeInterface(identifier)
        interface.setName(identifier)
        interface.setDescription(description)

        if adminstatus == "up":
            interface.setAdminStatus("up")
            if linkstatus == "down":
                interface.setLinkStatus("down")
            elif linkstatus == "up":
                interface.setLinkStatus("up")
            else:
                raise pynt.input.ParsingException("Unknown link/protocol status '%s' of interface %s" % (linkstatus, identifier))
        elif adminstatus != "down":
            raise pynt.input.ParsingException("Unknown admin/protocol status '%s' of interface %s" % (adminstatus, identifier))
        else:
            interface.setAdminStatus("down")

        # Configure the logical interfaces and adaptations
        macadapt    = pynt.technologies.ethernet.GetCreateWellKnownAdaptationFunction("MAC-in-Ethernet")
        taggedadapt = pynt.technologies.ethernet.GetCreateWellKnownAdaptationFunction("Tagged-Ethernet")
        gigethadapt = pynt.technologies.wdm.GetCreateWellKnownAdaptationFunction("eth1000base-X")
        lanphyadapt = pynt.technologies.wdm.GetCreateWellKnownAdaptationFunction("eth10Gbase-R")
        wanphyadapt = pynt.technologies.tdm.GetCreateWellKnownAdaptationFunction("WANPHY")
        oc192adapt  = pynt.technologies.wdm.GetCreateWellKnownAdaptationFunction("oc192-in-Lambda")
        wdmadapt    = pynt.technologies.wdm.GetCreateWellKnownAdaptationFunction("WDM")
        #basetadapt  = pynt.technologies.copper.GetCreateWellKnownAdaptationFunction("base-T")

        # Based on the description we create adaptations. Possible types are LAN PHY (10GbLR) and WAN PHY (10GbLW)
        if description in ["10GbLR"]:
            interface.setCapacity(1250000000) # 1250000000 Byte/s = 10.000 Gb/s
            lambdainterface = interface.getCreateAdaptationInterface(pynt.technologies.wdm.LambdaInterface, identifierappend="-lambda", nameappend=" lambda")
            lambdainterface.setWavelenght(1310.00)
            interface.addServerInterface(lambdainterface, gigethadapt)
            identifier = interface.getIdentifier() + "-fiber"
            name = interface.getName() + " fiber"
            fiberinterface = lambdainterface.getCreateAdaptationInterface(pynt.technologies.wdm.FiberInterface, identifier=identifier, name=name)
            fiberinterface.setSpacing("SingleLambda") # only one wavelenght on the fiber
            fiberinterface.setCladding("SingleMode")
            fiberinterface.setConnector("LC")
            fiberinterface.setPolish("PC")
            lambdainterface.addServerInterface(fiberinterface, wdmadapt)
        elif description in ["10GbLW"]:
            interface.setCapacity(1188864000) # 1188864000 Byte/s = 9510.912 Mb/s
            oc192interface = interface.getCreateAdaptationInterface(pynt.technologies.tdm.OC192Interface, identifierappend="-oc192", nameappend=" OC192")
            interface.addServerInterface(oc192interface, wanphyadapt)
            identifier = interface.getIdentifier() + "-lambda"
            name = interface.getName() + " lambda"
            lambdainterface = oc192interface.getCreateAdaptationInterface(pynt.technologies.wdm.LambdaInterface, identifier=identifier, name=name)
            lambdainterface.setWavelenght(1310.00)
            oc192interface.addServerInterface(lambdainterface, oc192adapt)
            oc192interface.setCapacity(1244160000)
            identifier = interface.getIdentifier() + "-fiber"
            name = interface.getName() + " fiber"
            fiberinterface = lambdainterface.getCreateAdaptationInterface(pynt.technologies.wdm.FiberInterface, identifier=identifier, name=name)
            fiberinterface.setSpacing("SingleLambda") # only one wavelenght on the fiber
            fiberinterface.setCladding("SingleMode")
            fiberinterface.setConnector("SC")
            fiberinterface.setPolish("PC")
            lambdainterface.addServerInterface(fiberinterface, wdmadapt)
    
    def parseVlans(self, vlanlines):
        """Parses the vlan string and configures vlans for all found interfaces."""
        for line in vlanlines:
            self.parseVlanLine(line)
        return len(vlanlines)
    
    def parseVlanLine(self, vlanString):
        """Parses one Vlan line, creating interface objects if necessary"""
        splitString = vlanString.split()
        num_elements = len(splitString)
        if num_elements < 7:        # not a valid vlan line
            return
        identifier      = splitString[0]    # blade/port format
        sendtagged      = splitString[1]    # "enable" or "disable"
        discardtagged   = splitString[2]    # "true" or "false". if true, discard received tagged frames
        discarduntagged = splitString[3]    # "true" or "false". if true, discard received tagged frames
        defaultvlan     = splitString[4]
        vlans           = splitString[5:-2] # VLAN IDs (both tagged and untagged)
        porttype        = splitString[-2]   # "normal"
        untagdefvlan    = splitString[-1]   # "enable" / "disable"
        # If untagdefvlan is enabled, untagged frames are treated as if the were tagged with the default vlan
        logger = logging.getLogger("pynt.device")
        interface = self.subject.getCreateNativeInterface(identifier)
        ports = splitString[0].split('/')
        interface.setBlade(ports[0])
        interface.setPort(ports[1])
        if (untagdefvlan != "disable"):
            logger.warning('Interface %s treats untagged frames as if they are tagged (with the default VLAN ID). This is unsupported by the Ethernet model' % (identifier))
        if (porttype != "normal"):
            raise pynt.input.ParsingException('Interface %s has type %s. I only understand type normal.' % (identifier, porttype))
        if sendtagged == "disable":
            # interface is untagged
            #print "%s: untagged, vlan %s, vlans %s" % (identifier, defaultvlan, vlans)
            if (sendtagged == "disable") and (discardtagged != "false"):
                logger.warning('Interface %s is tagged, but does not discard tagged frames. This is unsupported by the Ethernet model' % (identifier))
            if (len(vlans) != 1) or (vlans[0] != defaultvlan):
                raise pynt.input.ParsingException("Interface %s is untagged (in VLAN %s), but also has it's VLANs set to %s. That is inconsistent." % (identifier, defaultvlan, str(vlans)))
            vlan = self.subject.getCreateVlan(int(defaultvlan))
            self.subject.AddUntaggedInterface(vlan, interface)
        elif sendtagged == "enable":
            # interface is tagged
            #print "%s:   tagged, vlan %s, vlans %s" % (identifier, defaultvlan, vlans)
            if (sendtagged == "enable") and (discarduntagged != "false"):
                logger.warning('Interface %s is untagged, but does not discard untagged frames. This is unsupported by the Ethernet model' % (identifier))
            for vlanid in vlans:
                vlan = self.subject.getCreateVlan(int(vlanid))
                self.subject.AddTaggedInterface(vlan, interface)
        else:
            raise pynt.input.ParsingException("Unknown tagging status '%s' of interface %s" % (sendtagged, identifier))
    
        #splitString[6]=MAC address
        #splitString[7]=admin status: up/down
        #splitString[8]=link status: up/down
        #if num_elements >= 9:
        #    identifier = splitString[0]
        #    interface = self.subject.getCreateNativeInterface(identifier)
        #    interface.setSpeed(splitString[2])
        #    interface.setStatus_admin(splitString[7])
        #    interface.setOperate(splitString[8])
        return
