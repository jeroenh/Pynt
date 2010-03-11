# -*- coding: utf-8 -*-
"""The glimmerglass module contains a parsers which retrieves information from a Glimmerglass OXC device using TL1"""

# builtin modules
import logging
# local modules
import pynt.protocols.tl1
import pynt.elements
import pynt.xmlns

import pynt.input
import pynt.technologies.wdm     # defines FiberInterface class
# TODO: treat multicast differently! Don't show those ports, but directly describe switchedTo.
# requires us to either retrieve multicast config, or describe it here.

class OXCFetcher(pynt.input.BaseDeviceFetcher):
    """Fetches information from a Glimmerglass optical cross connect using the TL1 interface"""
    def __init__(self, *args, **params):
        pynt.input.BaseDeviceFetcher.__init__(self, *args, **params)
        self.subjectClass    = pynt.technologies.wdm.OXCDevice
        # TODO: are these properties of the fetcher, or of the device (I'd say: move to device, in technologies.wdm.OXCDevice)
        self.multicastports = {
                # the key is the egress port, which is an input port for multicast (data is sent TO multicast)
                # the value is a list of egress (input): ingress (output)
                # It is assumed that a port listed here should never be exposed to the outside world.
                # TODO: find this info based on port names (e.g. "MC-1-1", "MC-1")
                67: [67, 68, 69, 70],   # multicast input A: A1, A2, A3, A4
                68: [71, 72],           # multicast input B: B1, B2
                69: None,               # dead end: output not leading to actual port
                70: None,               # dead end: output not leading to actual port
                71: None,               # dead end: output not leading to actual port
                72: None,               # dead end: output not leading to actual port
            }
        self.unusedports = [65,66]
        # we need to have an intermediate state for multicast ports, to handle
        # 1 ---> A > A3 ---> B > B1 ---> 2          (---> = configured, > = static)
        # but if we first get the (A >) A3 ---> B (> B1,B2) information; we need to assign that to A somehow.
        # we store this in multicastconfig:  multicastconfig[67] = [71, 72]
        self.multicastconfig = {}
        # we have to handle loops: A3 ---> B > B1 ---> A > A3 etc.
    
    def setSourceHost(self, hostname, port=None):
        if not port:
            port = 10033
        self.io = pynt.protocols.tl1.SyncTL1Input(hostname=hostname, port=port)
        # self.io = pynt.protocols.tl1.AsyncTL1Input(hostname=hostname, port=port)
        self.io.setDefaultTimeout(10) # the Glimmerglass is quite fast.
        self.io.hasecho = True
    
    def setSourceFile(self, filename, hostname=None):
        self.io = pynt.protocols.tl1.TL1EmulatorInput(filename=filename)
        self.io.setPrompt("<")
    
    def retrieve(self):
        # get information from device
        self.subject.setDescription("%s Glimmerglass OXC" % self.identifier)
        # Retrieve information on fiber crossconnects, for all interfaces. Also returns information about unconnected interfaces (both input and output interfaces)
        # The PCAT filters only normal ports (thus not reference ports, like multicast ports)
        # TODO: If PCAT the correct filter, or should we specify PALIVE=... instead (todo: test with RTRV-PLIST)
        commandString = "rtrv-cfg-fiber::all:ctag;";
        crossconnectlines = self.io.command(commandString)
        self.parsePortNames(crossconnectlines)    # sets subject.interfaces
        
        commandString = "rtrv-crs-fiber::%s:ctag;" % (self.getportlist());
        crossconnectlines = self.io.command(commandString)
        self.parseCrossLines(crossconnectlines)    # sets subject.interfaces
    
    def getportlist(self, ports=None):
        """input: array of ports. output: string port list for use in TL1 commands"""
        if ports == None:
            return "all"
        else:
            pliststr = "";
            for port in ports:
                if pliststr != "": pliststr = pliststr + "&";
                pliststr = pliststr + str(10000 + int(port)) + "&" + str(20000 + int(port));
    
    def parsePortNames(self, interfaceLines):
        """
        Parses the Interface string and seperates the different interfaces. Creates interfaces 
        for normal ports with privileges > 0, set unusedports for normal ports with privileges = 0,
        and set multicastports for reference ports, based on the name (e.g. MC-*)
        """
        for line in interfaceLines:
            self.parsePortName(line)
        return len(interfaceLines)
    
    def parsePortName(self, interfaceString):
        "Parses one Interface line and returns an interface object"
        # InterfaceString looks like:
        # "GGN:PORTID=10064,PORTNAME=from 5530-stack #4,PORTDIR=input,PORTHEALTH=good,PORTCAT=nor,PORTPRIV=0x1"
        # "GGN:PORTID=20064,PORTNAME=to 5530-stack #4,PORTDIR=output,PORTHEALTH=good,PORTCAT=nor,PORTPRIV=0x1"
        # "GGN:PORTID=10065,PORTNAME=,PORTDIR=input,PORTHEALTH=good,PORTCAT=nor,PORTPRIV=0x0"
        # "GGN:PORTID=20065,PORTNAME=,PORTDIR=output,PORTHEALTH=good,PORTCAT=nor,PORTPRIV=0x0"
        # "GGN:PORTID=10067,PORTNAME=MC-1-1,PORTDIR=input,PORTHEALTH=good,PORTCAT=ref,PORTPRIV=0x1"
        # "GGN:PORTID=20067,PORTNAME=MC-1,PORTDIR=output,PORTHEALTH=good,PORTCAT=ref,PORTPRIV=0x1"
        # InterfaceString looks like:
        
        # First turn the line into a dictionary
        interfaceString = interfaceString.split(":")    # e.g. ["GGN", "PORTID=10064,PORTNAME=from 5530-stack #4,PORTDIR=input,PORTHEALTH=good,PORTCAT=nor,PORTPRIV=0x1"]
        properties = pynt.protocols.tl1.ParseSectionBlock(interfaceString[1])  # e.g. {PORTID:"10064",IPORTNAME:"from 5530-stack #4",PORTDIR:"input",...}
        logger = logging.getLogger("pynt.device")
        portid = int(properties['portid'])
        io = None
        if (portid >= 20000) and (portid < 30000):
            portid  = portid - 20000
            io = "out"
        elif (portid >= 10000) and (portid < 20000):
            portid  = portid - 10000
            io = "in"
        else:
            raise pynt.input.ParsingException('Found interface with id %s. Expected id in range 10000...29999.' % (portid))
        if properties['portcat'] == 'nor':
            if properties['portpriv'] == '0x0':
                # unused interface
                if portid not in self.unusedports:
                    logger.debug("Skipping unused port (privilege=0x0) %s" % portid)
                    self.unusedports.append(portid)
            else:
                # regular interface
                identifier = self.getIdenitifier(portid)
                interface = self.subject.getCreateNativeInterface(identifier)  # create Interface object or return existing one
                interface.setName(str(portid))
                interface.setPort(portid)
                switchmatrix = self.subject.getSwitchMatrix() # assume we only have one switch matrix (defined in OXCDevice class)
                switchmatrix.addInterface(interface)
                if 'portname' in properties and (str(properties['portname']) != ""):
                    portname = properties['portname']
                    if portname.startswith("from "):
                        if io == "out":
                            logger.warning('Output portname of port %s starts with "from": "%s"' % (str(portid), portname));
                        portname = portname[5:]
                    if portname.startswith("to "):
                        if io == "in":
                            logger.warning('Input portname of port %s starts with "to": "%s"' % (str(portid), portname));
                        portname = portname[3:]
                    if interface.getDescription() not in (None, "", portname):
                        if io == "in":
                            logger.warning('Input portname of port %s is "%s", but output portname is "%s".' % (str(portid), portname, interface.getDescription()));
                        else: 
                            logger.warning('Output portname of port %s is "%s", but input portname is "%s".' % (str(portid), interface.getDescription(), portname));
                    interface.setDescription(portname)
        elif properties['portcat'] == 'ref':
            # multicast interface
            if portid not in self.unusedports:
                logger.debug("Skipping special (multicast, etc.) port %s" % portid)
                self.unusedports.append(portid)
            # interface.getDescription().lower().startswith("mc-") and not interface.getDescription().lower().startswith("multicast")            # TODO: implement or log a warning for the time being
            pass
    
    def parseCrossLines(self, interfaceLines):
        """
        Parses the Interface string and seperates the different interfaces
        Returns a list of interface objects.
        """
        for line in interfaceLines:
            self.parseCrossLine(line)
        return len(interfaceLines)
    
    def getIdenitifier(self,portno):
        return "intf%02d" % portno
    
    def parseCrossLine(self, interfaceString):
        "Parses one Interface line and returns an interface object"
        # InterfaceString looks like:
        # "GGN:IPORTID=10042,IPORTNAME=from BeautyCees 13b.2,OPORTID=20058,OPORTNAME=to Force10 gi5/9,CONNID=0,CONNSTATE=steady,CONNCAUSE=none,INPWR=-12.618,OUTPWR=-14.277,PWRLOSS=1.672,CONNLOCK=0,CONNLOCKUSER=admin"
        
        # First turn the line into a dictionary
        logger = logging.getLogger("pynt.device")
        interfaceString = interfaceString.split(":")    # e.g. ["GGN", "IPORTID=10042,IPORTNAME=from BeautyCees 13b.2,OPORTID=20058"]
        properties = pynt.protocols.tl1.ParseSectionBlock(interfaceString[1])  # e.g. "IPORTID=10042,IPORTNAME=from BeautyCees 13b.2,OPORTID=20058"
        inport  = int(properties['iportid']) - 10000;
        outport = int(properties['oportid']) - 20000;
        
        # TODO: treat specially for multicast and/or unused ports
        if inport in self.unusedports:
            logger.debug("Skipping crossconnect information for unused port %s" % inport)
            return
        if outport in self.unusedports:
            logger.debug("Skipping crossconnect information for unused port %s" % outport)
            return
        
        # check if the line contains information on an input port
        logger = logging.getLogger("pynt.device")
        if inport >= 0:
            identifier = self.getIdenitifier(inport)
            interface = self.subject.getCreateNativeInterface(identifier)  # create Interface object or return existing one
            interface.setName(str(inport))
            interface.setPort(inport)
            interface.setIngressPowerLevel(properties['inpwr'])
            if outport >= 0:
                identifier = self.getIdenitifier(outport)
                interface.addSwitchedInterface(self.subject.getCreateNativeInterface(identifier))
        # check if the line contains information on an output port
        if outport >= 0:
            identifier = self.getIdenitifier(outport)
            interface = self.subject.getCreateNativeInterface(identifier)  # create Interface object or return existing one
            interface.setName(str(outport))
            interface.setPort(outport)
            interface.setEgressPowerLevel(properties['outpwr'])
            if inport >= 0:
                identifier = self.getIdenitifier(inport)
                self.subject.getCreateNativeInterface(identifier).addSwitchedInterface(interface)

