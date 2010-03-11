# -*- coding: utf-8 -*-
"""The force10 module contains a parsers which retrieves information from a Force10 device using the command line interface"""

# builtin modules
import os
import logging
# local modules
import pynt.protocols.cli
import pynt.elements
import pynt.xmlns
import pynt.input

import pynt.technologies.ethernet     # defines FiberInterface class
import pynt.technologies.ip
import pynt.technologies.tdm
import pynt.technologies.wdm
import pynt.technologies.copper

class EtherscaleFetcher(pynt.input.BaseDeviceFetcher):
    """Fetches information from a Force10 E-series Ethernet switch"""
    quitCmd         = 'quit'
    def __init__(self, *args, **params):
        pynt.input.BaseDeviceFetcher.__init__(self, *args, **params)
        self.subjectClass    = pynt.technologies.ethernet.EthernetDevice
    
    def setSourceHost(self, hostname, port=None):
        self.io = pynt.protocols.cli.SSHInput(hostname=hostname, port=port)
        self.io.setDefaultTimeout(30)
        self.io.setPrompt(self.identifier.capitalize()+">")
    
    def setSourceFile(self, filename, hostname=None):
        self.io = pynt.protocols.cli.CLIEmulatorInput(filename=filename)
        if hostname:
            identifier = hostname.split(".")[0]
        else:
            identifier = os.path.basename(filename)
        self.io.setPrompt(identifier.capitalize()+">")
    
    def command(self, command, skipStartLines=0, lastSkipLineRe=None, skipEndLines=0):
        resultLines = self.io.command(command)
        return pynt.protocols.cli.ParseCLILines(resultLines, skipStartLines=skipStartLines, lastSkipLineRe=lastSkipLineRe, skipEndLines=skipEndLines)
    
    def retrieve(self):
        # get information from device
        # self.command("show calendar")
        self.command("terminal length 0")   # turn off interactive shell
        interfacelines   = self.command('show interfaces description', skipStartLines=1)
        vlanlines        = self.command('show vlan', skipStartLines=4, lastSkipLineRe=".*Q Ports.?")
        bladelines       = self.command('show linecard all', skipStartLines=4, lastSkipLineRe="\-\-+")
        # TODO: get more info from interfaces using "show interfaces" and extract MAC address, MTU, IP address (if any), ingress & egress data rate
        interfacedetails = []
        #interfacedetails = self.io.command('show interfaces')
        
        # Note: the blades must come before the others
        self.parseInterfaces(interfacelines)    # sets subject.interfaces
        self.parseBlades(bladelines)            # sets subject.blades
        self.parseVlans(vlanlines)              # sets subject.vlans
        self.addLogicalInterfacePerBlade()
        self.addLogicalMACInterfaces()
        self.parseInterfaceDetails(interfacedetails)
        # add logical interfaces to physical interfaces based on blades
    
    def parseInterfaces(self, interfaceLines):
        """
        Parses the Interface string and seperates the different interfaces
        Returns a list of interface objects.
        """
        for line in interfaceLines:
            self.parseInterfaceLine(line)
        return len(interfaceLines)
    
    def parseInterfaceLine(self, interfaceString):
        "Parses one Interface line and returns an interface object"
        # InterfaceString looks like:
        # "Interface               OK? Status     Protocol    Description"
        # "TenGigabitEthernet 4/1  NO  admin down down        Speculaas #15"
        # "Vlan 4                  YES up         up          Netherlight normal MTU sized vlan"
        # "ManagementEthernet 1/0  NO  admin down not present"
        ifname      = interfaceString[0:24].rstrip()
        okstatus    = interfaceString[24:28].rstrip() # "YES", "NO"
        adminstatus = interfaceString[28:39].rstrip() # "up", "admin down"
        linkstatus  = interfaceString[39:51].rstrip() # "up", "down", "not present"
        description = interfaceString[51:].rstrip()
        
        result = False  # return True if a new interface or vlan object was created
        if ifname == "":  # skip empty lines
            return False
        ifnamesplit = ifname.split(); # e.g. "TenGigabitEthernet 4/1" => ["TenGigabitEthernet","4/1"]
        speedtype = ifnamesplit[0]    # e.g. "TenGigabitEthernet"
        if len(ifnamesplit) > 1:
            ifid = ifnamesplit[1]     # e.g. "4/1"
        if (speedtype in ["GigabitEthernet", "TenGigabitEthernet"]):
            if speedtype == "TenGigabitEthernet":
                prefix = 'te';
            else:  # GigabitEthernet
                prefix = 'gi';
            name = prefix+ifid
            identifier = name
            try:
                (blade,port) = ifid.split('/');
            except ValueError:
                raise pynt.input.ParsingException("The interface ID is '%s', which is not in the expected 0/0 format." % ifid)
            
            interface = self.subject.getCreateNativeInterface(identifier)  # create Interface object or return existing one
            interface.setName(name)
            result = True
            interface.setPrefix(prefix)
            if blade.isdigit():
                interface.setBlade(int(blade))
            else:
                raise pynt.input.ParsingException("Expected blade '%s' of interface %s to be a number" % (blade, name))
            if port.isdigit():
                interface.setPort(int(port))
            else:
                raise pynt.input.ParsingException("Expected port '%s' of interface %s to be a number" % (port, name))
            if description:
                interface.setDescription(description)
            # okstatus = combination of linkstatus and adminstatus: not stored
            if (adminstatus in ["admin down", "down"]):
                interface.setAdminStatus("down");
            elif (adminstatus in ["up"]):
                interface.setAdminStatus("up");
            else: 
                raise pynt.input.ParsingException("Unkown admin status '%s' of interface %s" % (adminstatus, name))
            if (adminstatus == "up"):
                # If adminstatus is down, the link status is not measured and always "down", even if light is received
                if (linkstatus in ["not present", "down"]):
                    interface.setLinkStatus("down");
                elif (linkstatus in ["up"]):
                    interface.setLinkStatus("up");
                else: 
                    raise pynt.input.ParsingException("Unkown link/protocol status '%s' of interface %s" % (linkstatus, name))
        elif (speedtype in ["Vlan"]):
            vlan = self.subject.getCreateVlan(ifid)
            result = True
            if (adminstatus == "admin down"):
                adminstatus = "down"
            vlan.setAdminStatus(adminstatus);
            # We're currently not storing the "link status"; this is always up, and doesn't seem to have a real meaning
            # if (linkstatus == "not present"):
            #     linkstatus = "down"
            # vlan.setLinkStatus(linkstatus);
            vlan.setDescription(description)
        elif (speedtype in ["ManagementEthernet"]):
            # skip management interfaces
            pass
        else:
            raise pynt.input.ParsingException("Skipping unknown interface '%s'" % ifname)
        return result
    
    def parseVlans(self, vlanLines):
        """
        Parses the VLAN table string and seperates the different vlans which
        are then processed by parseVlanId.
        Returns the numnber of detected vlans.
        """
        vlancount = 0;
        for line in vlanLines:
            # vlanLines looks like:
            # "    NUM    Status    Q Ports"
            # "*   3      Active    U Gi 1/0,6-11,15,23"
            # "                     U Te 4/1"
            # "    4      Active    T Te 6/0"
            # "    5      Inactive  U Gi 1/1-5,16-22"
            modifier    = line[0:4].rstrip()    # "*", "G"
            vlanid      = line[4:11].rstrip()   # integer
            adminstatus = line[11:21].rstrip()  # "Active", "Inactive"
            tagged      = line[21:23].rstrip()  # "U", "T"
            ports       = line[23:].rstrip()    # e.g. "Gi 1/0,6-11,15,23"
            if (vlanid):
                # new line with new VLAN
                if not vlanid.isdigit():
                    raise pynt.input.ParsingException("Expected a VLAN ID, but %s is not a number in '%s'" % (vlanid, line))
                vlan = self.subject.getCreateVlan(int(vlanid))
                vlancount += 1
            if not vlan:
                raise pynt.input.ParsingException("Expected the first line of vlan list to start with a VLAN ID, but got '%s'" % (line))
            if (adminstatus in ["Active", "Inactive"]):
                vlan.setAdminStatus(adminstatus)
            elif adminstatus:
                raise pynt.input.ParsingException("Skipping unknown adminstatus '%s' of VLAN %s" % (adminstatus, vlanid))
            
            # convert the "Gi 1/0,6-11,15,23" string to tuplets of the form [("gi",1,0),("gi",1,6),...,("gi",1,23)]
            portlist = self.parseVlanPorts(ports)
            for (prefix,blade,port) in portlist:
                identifier = pynt.elements.InterfaceIdentifier(prefix, blade, port)
                interface = self.subject.getCreateNativeInterface(identifier)
                if (tagged == "U"):
                    self.subject.AddUntaggedInterface(vlan, interface)
                elif (tagged == "T"):
                    self.subject.AddTaggedInterface(vlan, interface)
                else:
                    raise pynt.input.ParsingException("Unknown 'Q' status '%s' for ports '%s' in VLAN %s (expected U or T)" % (tagged, ports, vlanid))
        return vlancount
    
    def parseVlanPorts(self, portsString):
        """
        Force10 specific PortsString parser.
        Parses strings of the form:
            'Gi 1/0,16-21,23'
        to 
            [(1,0,'gi'),(1,16,'gi'), ... ,(1,21,'gi'), (1,23,'gi')] 
        """
        prefix      = portsString[0:3].rstrip().lower() # "gi" or "te"
        portsString = portsString[3:].rstrip()          # e.g. "1/0,16-21,23"
        # Ports are listed per blade
        if (portsString == ""):
            return [];   # empty list
        try:
            (blade,portnums) = portsString.split('/');
        except ValueError:
            raise pynt.input.ParsingException("The port list '%s' is not in the expected '1/0,16-21,23' format." % portsString)
        if not blade.isdigit():
            raise pynt.input.ParsingException("Expected a port range, but blade %s in range %s is not a number" % (blade, portsString))
        
        resultPorts = []
        # The portnumbers can be lists
        # of the form 0,16-21,23
        for num in portnums.split(','):
            if '-' in num:
                # There is a range (like 16-21)
                low,high = num.split('-')
                if not low.isdigit():
                    raise pynt.input.ParsingException("Expected a port range, but lower limit %s in range %s is not a number" % (low, portsString))
                if not high.isdigit():
                    raise pynt.input.ParsingException("Expected a port range, but upper limit %s in range %s is not a number" % (high, portsString))
                for port in range(int(low),int(high)+1):
                    resultPorts.append((prefix, int(blade), port))
            else:
                # The number given is just a single number
                if not num.isdigit():
                    raise pynt.input.ParsingException("Expected a port range, but port %s in range %s is not a number" % (num, portsString))
                resultPorts.append((prefix, int(blade),int(num)))
        return resultPorts
    
    def parseBlades(self, bladesString):
        """
        Parses the Blades string and seperates the different interfaces
        Returns a list of interface objects.
        """
        for line in bladesString:
            # "Slot  Status        NxtBoot    ReqTyp   CurTyp   Version     Ports"
            # "  0   online        online     E24TD    E24TD    5.3.1.6     24  "
            bladeno     = line[0:6].strip()     # "0"
            adminstatus = line[6:20].rstrip()   # "online", "not present"
            bootstatus  = line[20:31].rstrip()  # "online", ""
            reqtype     = line[31:40].rstrip()  # "E24TD", "EX2YD", "EW2YE", "E24PD", ""
            curtype     = line[40:49].rstrip()  # "E24TD", "EX2YD", "EW2YE", "E24PD", ""
            version     = line[49:61].rstrip()  # "5.3.1.6"
            portcount   = line[61:].rstrip()    # integer
            
            if bladeno == "":
                continue
            if not bladeno.isdigit():
                raise pynt.input.ParsingException("Expected bladeno '%s' to be an integer in line '%s'" % (bladeno, line))
            blade = self.subject.getCreateBlade(int(bladeno))
            blade.setVendorType(curtype)
            blade.setSWVersion(version)
            blade.setAdminStatus(adminstatus)
            if portcount == "":
                portcount = "0"
            if not portcount.isdigit():
                raise pynt.input.ParsingException("Expected portcount '%s' to be an integer in line '%s'" % (portcount, line))
            blade.setPortCount(int(portcount))
            description = ""
            if curtype == "E24TD":
                description = "E24TD is a blade of 24 UTP connectors at 1 Gbit/s Ethernet";
            elif curtype == "E24PD":
                description = "E24PD is a blade of 24 SFP transceivers for 1 Gbit/s Ethernet";
            elif curtype == "EX2YD":
                description = "EX2YD is a blade of 2 SC connectors for 10 Gbit/s Ethernet (LAN PHY)";
            elif curtype == "EW2YE":
                description = "EW2YE is a blade of 2 SC connectors for 9.5 Gbit/s Ethernet (WAN PHY)";
            blade.setDescription(description)
        
    def parseInterfaceDetails(self, interfacedetails):
        """
        Parses interface defintion lines. These are very lengthy.
        Most information is skipped.
        """
        ipadapt     = pynt.technologies.ethernet.GetCreateWellKnownAdaptationFunction("IP-in-MAC")
        macadapt    = pynt.technologies.ethernet.GetCreateWellKnownAdaptationFunction("MAC-in-Ethernet")
        # TODO: to be written
        
        # GigabitEthernet 0/0 is up, line protocol is down
        # Description: gi7-1.sara-r1.rtr.sara.nl
        # Hardware is Force10Eth, address is 00:01:e8:02:e0:8f
        # Internet address is not set
        # MTU 9252 bytes, IP MTU 9234 bytes
        # LineSpeed auto, Mode full duplex
        # LineSpeed 1000 Mbit, Mode full duplex
        #      Input 00.00Mbits/sec,          0 packets/sec
        #      Output 00.00Mbits/sec,          0 packets/sec
        pass
    
    def addLogicalInterfacePerBlade(self):
        """add logical interfaces to physical interfaces based on blade types"""
        #import pynt.technologies.ip
        macadapt    = pynt.technologies.ethernet.GetCreateWellKnownAdaptationFunction("MAC-in-Ethernet")
        taggedadapt = pynt.technologies.ethernet.GetCreateWellKnownAdaptationFunction("Tagged-Ethernet")
        gigethadapt = pynt.technologies.wdm.GetCreateWellKnownAdaptationFunction("eth1000base-X")
        lanphyadapt = pynt.technologies.wdm.GetCreateWellKnownAdaptationFunction("eth10Gbase-R")
        wanphyadapt = pynt.technologies.tdm.GetCreateWellKnownAdaptationFunction("WANPHY")
        oc192adapt  = pynt.technologies.wdm.GetCreateWellKnownAdaptationFunction("oc192-in-Lambda")
        wdmadapt    = pynt.technologies.wdm.GetCreateWellKnownAdaptationFunction("WDM")
        basetadapt  = pynt.technologies.copper.GetCreateWellKnownAdaptationFunction("base-T")
        
        for interface in self.subject.getNativeInterfaces():
            bladeno = interface.getBlade()
            blade = self.subject.getCreateBlade(bladeno)
            vendortype = blade.getVendorType()
            if vendortype == "E24TD":
                # E24TD is a blade of 24 UTP connectors at 1 Gbit/s Ethernet
                interface.setCapacity(125000000) # 125000000 Byte/s = 1000 Mb/s
                utpinterface = interface.getCreateAdaptationInterface(pynt.technologies.copper.TwistedPairInterface, identifierappend="-copper", nameappend=" copper")
                interface.addServerInterface(utpinterface, basetadapt)
            elif vendortype == "E24PD":
                # E24PD is a blade of 24 SFP transceivers for 1 Gbit/s Ethernet
                interface.setCapacity(125000000) # 125000000 Byte/s = 1000 Mb/s
                lambdainterface = interface.getCreateAdaptationInterface(pynt.technologies.wdm.LambdaInterface, identifierappend="-lambda", nameappend=" lambda")
                # we assume the SPF lasers are 1310nm
                lambdainterface.setWavelenght(1310.00)
                interface.addServerInterface(lambdainterface, gigethadapt)
                identifier = interface.getIdentifier() + "-fiber"
                name = interface.getName() + " fiber"
                fiberinterface = lambdainterface.getCreateAdaptationInterface(pynt.technologies.wdm.FiberInterface, identifier=identifier, name=name)
                fiberinterface.setSpacing("SingleLambda") # only one wavelenght on the fiber
                fiberinterface.setCladding("SingleMode")
                fiberinterface.setConnector("LC")
                fiberinterface.setPolish("PC")
                fiberinterface.setTransceiver("SFP")
                lambdainterface.addServerInterface(fiberinterface, wdmadapt)
            elif vendortype == "EX2YD":
                # EX2YD is a blade of 2 SC connectors for 10 Gbit/s Ethernet (LAN PHY)
                interface.setCapacity(1250000000) # 1250000000 Byte/s = 10.000 Gb/s
                lambdainterface = interface.getCreateAdaptationInterface(pynt.technologies.wdm.LambdaInterface, identifierappend="-lambda", nameappend=" lambda")
                lambdainterface.setWavelenght(1310.00)
                interface.addServerInterface(lambdainterface, gigethadapt)
                identifier = interface.getIdentifier() + "-fiber"
                name = interface.getName() + " fiber"
                fiberinterface = lambdainterface.getCreateAdaptationInterface(pynt.technologies.wdm.FiberInterface, identifier=identifier, name=name)
                fiberinterface.setSpacing("SingleLambda") # only one wavelenght on the fiber
                fiberinterface.setCladding("SingleMode")
                fiberinterface.setConnector("SC")
                fiberinterface.setPolish("PC")
                lambdainterface.addServerInterface(fiberinterface, wdmadapt)
            elif vendortype == "EW2YE":
                # EW2YE is a blade of 2 SC connectors for 9.5 Gbit/s Ethernet (WAN PHY)
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
    
    def addLogicalMACInterfaces(self):
        """add logical interfaces to physical interfaces based on blade types"""
        # TODO: to be written
        macadapt    = pynt.technologies.ethernet.GetCreateWellKnownAdaptationFunction("MAC-in-Ethernet")
        taggedadapt = pynt.technologies.ethernet.GetCreateWellKnownAdaptationFunction("Tagged-Ethernet")
        
        for interface in self.subject.getNativeInterfaces():
            pass
    


