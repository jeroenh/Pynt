# -*- coding: utf-8 -*-
"""The Calient module contains a parsers which retrieves information from a Calient PX or PXC device using TL1""" 

# builtin modules
import re
import logging
import time
# local modules
import pynt.input
import pynt.protocols.tl1
import pynt.elements
import pynt.xmlns

import pynt.technologies.wdm     # defines FiberInterface class

class PXCFetcher(pynt.input.BaseDeviceFetcher):
    """Fetches information from a Calient PXC optical cross connect using the TL1 interface"""
    def __init__(self, *args, **params):
        pynt.input.BaseDeviceFetcher.__init__(self, *args, **params)
        self.subjectClass    = pynt.technologies.wdm.OXCDevice
    # The calient if sometimes so frustratingly slow, that we have to emulate some functions
    # e.g. just getting the list of interfaces takes a minute....
    if_name_src = 'local'; # "none", "online", "local"
    blade = "10"
    
    # Timing measurements:
    #                                 synchronous   asynchronous
    # retrieve crosses only             73 sec         50 sec
    # retrieve ports and crosses       436 sec        173 sec
    # 
    # So asynchronous is considerably faster.
    
    
    def setSourceHost(self, hostname, port=None):
        if not port:
            port = 3082
        self.io = pynt.protocols.tl1.AsyncTL1Input(hostname=hostname, port=port)
        # self.io = pynt.protocols.tl1.SyncTL1Input(hostname=hostname, port=port)
        self.io.setDefaultTimeout(60)
    
    def setSourceFile(self, filename, hostname=None):
        self.io = pynt.protocols.tl1.TL1EmulatorInput(filename=filename)
        self.io.setPrompt("agent> ")
    
    def retrieve(self):
        # We sleep for a while, since the Calient screws up sometimes: 
        # giving a "Login Not Active" if the first command comes too fast after the ACT-USER command
        # This in particular happens with Asynchronous connections somehow.
        time.sleep(0.5)
        # Compile the list of interfaces
        if self.if_name_src == 'online':
            # first retrieve a list of all interfaces
            commandString = "RTRV-PORT::%s:ctag;" % (self.blade);
            interfacelines = self.io.command(commandString, timeout=120) # Get yourself some coffee. This takes a while
            self.parseInterfaceListLines(interfacelines)
        else:
            self.setInterfacesOffline()
        
        # Next, loop over all given interfaces to get their name
        if self.if_name_src == 'local':
            self.setInterfaceNamesOffline()
        elif self.if_name_src == 'online':
            for interface in self.subject.getNativeInterfaces():
                # Unlike the PXC, the only way to get the interface description
                # is to loop over each individual interface and ask for it.
                # This PX gives that info when asked for all interfaces.
                # The PX does not. *SIGH*
                commandString = str("RTRV-PORT::%s:ctag;" % (interface.getName()) ); # name for us, identifier for calient
                self.io.callbackCommand(commandString, self.parsePortProperties)
                # self.parsePortProperties(self.io.command(commandString))

        switchmatrix = self.subject.getSwitchMatrix() # defined in OXCDevice class
        for interface in self.subject.getNativeInterfaces():
            switchmatrix.addInterface(interface)
        
        # Finally, we retrieve the set of cross connects, which 
        # -beside the obvious "switchedto"- contains information 
        # about the power levels as well.
        commandString = "RTRV-CRS:::ctag;";
        crosses = self.io.command(commandString, timeout=120) # Get yourself some coffee. This takes a while
        ##print "crosses = ", crosses
        crosslist = [];
        for crossconnect in crosses:
            crossconnect = crossconnect.split(":");     # split into different blocks (or sections)
            crossname = crossconnect[0];                # name of the crossconnect
            properties = pynt.protocols.tl1.ParseSectionBlock(crossconnect[1])  # e.g. "IPORTID=10042,IPORTNAME=from BeautyCees 13b.2,OPORTID=20058"
            
            crossname = properties['grpname']+','+crossname;
            crosslist.append(crossname);
            
            # regretfully. none of the properties in the results are useful.
            # we only need the GRPNAME (nearly always "SYSTEM") for the full 
            # name, so we can now ask for details for each cross connect.
            commandString = str("RTRV-CRS:::ctag::%s;" % (crossname) );
            self.io.callbackCommand(commandString, self.parseCrsProperties)
            # self.parseCrsProperties(self.io.command(commandString))
    
    def parsePortProperties(self, results):
        """Take the first line of a RTRV-PORT command, and extract the interesting properties."""
        results = results[0];           # extract only line from array
        results = results.split(":");   # split into different blocks (or sections)
        # first block is the name of the interface
        interface = self.subject.getCreateNativeInterface(self.nameToIdentifier(results[0]))
        properties = pynt.protocols.tl1.ParseSectionBlock(results[2])  # e.g. "IPORTID=10042,IPORTNAME=from BeautyCees 13b.2,OPORTID=20058"
        # Extract interesting properties to return
        if len(properties['alias']) > 0:
            interface.setDescription(properties['alias']);
    
    def parseCrsProperties(self, crosses):
        """Take the lines of a CRS-PORT command, and extract the interesting properties."""
        crossnameRE = re.compile('^(.*)([-><])(.*)$');  # e.g. "10.2a.4-10.3a.8" or "10.2a.4>10.3a.8"
        for cross in crosses:
            cross = cross.split(":");
            crossnamematch = crossnameRE.match(cross[0]);
            if crossnamematch == None:
                raise pynt.input.ParsingException("Don't understand output of RTRV-CRS (first label %s is not a cross connect name)" % cross[0])
                continue
            crossnamematch = crossnamematch.groups();
            srcport  = crossnamematch[0]
            destport = crossnamematch[2]
            srcinterface  = self.subject.getCreateNativeInterface(self.nameToIdentifier(srcport))
            destinterface = self.subject.getCreateNativeInterface(self.nameToIdentifier(destport))
            crosstype = crossnamematch[1]
            if crosstype == "-":
                srcinterface.addSwitchedInterface(destinterface)
                destinterface.addSwitchedInterface(srcinterface)
            elif crosstype == "<":
                destinterface.addSwitchedInterface(srcinterface)
            elif crosstype == ">":
                srcinterface.addSwitchedInterface(destinterface)
            else:
                # WARNING: unknown cross type
                pass
            
            properties = pynt.protocols.tl1.ParseSectionBlock(cross[1])  # e.g. "IPORTID=10042,IPORTNAME=from BeautyCees 13b.2,OPORTID=20058"
            
            if 'forwardworkingpowerinput'  in properties:
                srcinterface.setIngressPowerLevel(properties['forwardworkingpowerinput'])
            if 'reverseworkingpowerinput'  in properties:
                destinterface.setIngressPowerLevel(properties['reverseworkingpowerinput'])
            if 'forwardworkingpoweroutput' in properties:
                destinterface.setEgressPowerLevel(properties['forwardworkingpoweroutput'])
            if 'reverseworkingpoweroutput' in properties:
                srcinterface.setEgressPowerLevel(properties['reverseworkingpoweroutput'])
    
    def parseInterfaceListLines(self, interfaceLines):
        """
        Parses a long list of interface strings. 
        regretfully, we don't get more information about the interface. 
        Not even the alias (=human readable name). Otherwise, we could
        have added that information to the interfaces list here.
        """
        for interfaceline in interfaceLines:
            interfaceline = interfaceline.split(":");
            name = interfaceline[0];
            identifier = self.nameToIdentifier(name)
            interface = self.subject.getCreateNativeInterface(identifier)
            interface.setName(name)
    
    def getIdentifier(self,portno,name=False):
        """input:9; output: 0.1b.1. PXC specific."""
        portno = int(portno) - 1
        port     = 1 + (portno % 8)
        portno = portno / 8
        subblade = chr(ord('a') + (portno % 2))
        blade    = 1 + (portno / 2)
        chassis  = 0
        if name:
            return "%d.%d%s.%d" % (chassis, blade, subblade, port)
        else:
            return "%02d.%02d%s.%d" % (chassis, blade, subblade, port)
    
    def nameToIdentifier(self,identifier,name=False):
        """input: 0.1b.1; output: 9. PXC specific."""
        (chassis, blade, port) = identifier.split(".")
        subblade = blade[-1:]
        blade = int(blade[:-1])
        port = int(port)
        chassis = int(chassis)
        if name:
            return "%d.%d%s.%d" % (chassis, blade, subblade, port)
        else:
            return "%02d.%02d%s.%d" % (chassis, blade, subblade, port)
    
    def getPort(self,identifier):
        """input: 10.2a.1; output: 9. PXC specific."""
        (chassis, blade, port) = identifier.split(".")
        subblade = blade[-1:]
        subblade = ord(subblade) - ord('a') # 0 for a, 1 for b
        blade = int(blade[:-1])
        port = int(port)
        portno = 16*(blade-1) + 8*subblade + int(port)
        return portno
    
    def setInterfacesOffline(self):
        # PXC specific.
        maxportno = 64
        for portno in range(1,maxportno+1):
            interface = self.subject.getCreateNativeInterface(self.getIdentifier(portno))
            interface.setName(self.getIdentifier(portno, name=True))
    

class PXFetcher(PXCFetcher):
    """Fetches information from a Calient PXC optical cross connect using the TL1 interface
    The only difference between the PX and PXC is the naming of the interfaces."""
    blade = "10"
    
    def getIdentifier(self,portno,name=False):
        """input:9; output: 10.2a.1. PX specific."""
        portno = int(portno) - 1
        port     = 1 + (portno % 8)
        subblade = 'a'
        blade    = 1 + (portno / 8)
        chassis  = 10
        portno = 8*(blade-1) + port
        if name:
            return "%d.%d%s.%d" % (chassis, blade, subblade, port)
        else:
            return "%02d.%02d%s.%d" % (chassis, blade, subblade, port)
    
    def nameToIdentifier(self,identifier,name=False):
        """input: 10.2a.1; output: 9. PX specific."""
        (chassis, blade, port) = identifier.split(".")
        subblade = blade[-1:]
        blade = int(blade[:-1])
        port = int(port)
        chassis = int(chassis)
        if name:
            return "%d.%d%s.%d" % (chassis, blade, subblade, port)
        else:
            return "%02d.%02d%s.%d" % (chassis, blade, subblade, port)
    
    def getPort(self,identifier):
        """input: 10.2a.1; output: 9. PX specific."""
        (chassis, blade, port) = identifier.split(".")
        subblade = blade[-1:]
        subblade = ord(subblade) - ord('a') # 0 for a, 1 for b
        blade = int(blade[:-1])
        port = int(port)
        portno = 8*(blade-1) + int(port)
        return portno
    
    def setInterfacesOffline(self):
        # PX specific.
        maxportno = 128
        for portno in range(1,maxportno+1):
            interface = self.subject.getCreateNativeInterface(self.getIdentifier(portno))
            interface.setName(self.getIdentifier(portno, name=True))
    
    def setInterfaceNamesOffline(self):
        """Shortcut to get device names. Fetching from the Calient takes about 4 minutes (!)"""
        # TODO: read from file; this is ugly++.
        self.subject.getCreateNativeInterface('10.01a.1').setDescription('VANGOGH1')
        self.subject.getCreateNativeInterface('10.01a.2').setDescription('VANGOGH2')
        self.subject.getCreateNativeInterface('10.01a.3').setDescription('VANGOGH3')
        self.subject.getCreateNativeInterface('10.01a.4').setDescription('VANGOGH4')
        self.subject.getCreateNativeInterface('10.01a.5').setDescription('VANGOGH5')
        self.subject.getCreateNativeInterface('10.01a.6').setDescription('VANGOGH6')
        self.subject.getCreateNativeInterface('10.01a.7').setDescription('VANGOGH7')
        self.subject.getCreateNativeInterface('10.01a.8').setDescription('VANGOGH8')
        self.subject.getCreateNativeInterface('10.02a.1').setDescription('HOUDINI_2.1')
        self.subject.getCreateNativeInterface('10.02a.2').setDescription('HOUDINI_8.2')
        self.subject.getCreateNativeInterface('10.02a.3').setDescription('HOUDINI_2.3')
        self.subject.getCreateNativeInterface('10.02a.4').setDescription('HOUDINI_7.1')
        self.subject.getCreateNativeInterface('10.02a.5').setDescription('HOUDINI_7.2')
        self.subject.getCreateNativeInterface('10.02a.6').setDescription('HOUDINI_7.3')
        self.subject.getCreateNativeInterface('10.02a.8').setDescription('VLSR_1.1.4')
        self.subject.getCreateNativeInterface('10.03a.1').setDescription('SPECULAAS_34')
        self.subject.getCreateNativeInterface('10.03a.2').setDescription('SPECULAAS_36')
        self.subject.getCreateNativeInterface('10.03a.3').setDescription('SPECULAAS_37')
        self.subject.getCreateNativeInterface('10.03a.4').setDescription('SPECULAAS_38')
        self.subject.getCreateNativeInterface('10.03a.5').setDescription('SPECULAAS_39')
        self.subject.getCreateNativeInterface('10.03a.6').setDescription('SPECULAAS_40')
        self.subject.getCreateNativeInterface('10.03a.7').setDescription('SPECULAAS_42')
        self.subject.getCreateNativeInterface('10.03a.8').setDescription('SPECULAAS_43')
        self.subject.getCreateNativeInterface('10.04a.1').setDescription('NETGEAR_1GTRUNK')
        self.subject.getCreateNativeInterface('10.04a.2').setDescription('6509_1.11')
        self.subject.getCreateNativeInterface('10.04a.3').setDescription('6509_1.10')
        self.subject.getCreateNativeInterface('10.04a.4').setDescription('6509_1.9')
        self.subject.getCreateNativeInterface('10.04a.8').setDescription('LALA_24')
        self.subject.getCreateNativeInterface('10.05a.1').setDescription('HOUDINI_9.1')
        self.subject.getCreateNativeInterface('10.05a.2').setDescription('HOUDINI_10.1')
        self.subject.getCreateNativeInterface('10.05a.3').setDescription('HOUDINI_9.2')
        self.subject.getCreateNativeInterface('10.05a.4').setDescription('HOUDINI_10.2')
        self.subject.getCreateNativeInterface('10.05a.5').setDescription('HOUDINI_9.3')
        self.subject.getCreateNativeInterface('10.05a.6').setDescription('HOUDINI_10.3')
        self.subject.getCreateNativeInterface('10.06a.1').setDescription('BAD_6A1')
        self.subject.getCreateNativeInterface('10.06a.2').setDescription('SPECULAAS_31')
        self.subject.getCreateNativeInterface('10.06a.3').setDescription('SPECULAAS_32')
        self.subject.getCreateNativeInterface('10.06a.4').setDescription('SPECULAAS_33')
        self.subject.getCreateNativeInterface('10.06a.5').setDescription('SPECULAAS_10')
        self.subject.getCreateNativeInterface('10.07a.1').setDescription('HDXC_506_1')
        self.subject.getCreateNativeInterface('10.07a.2').setDescription('HDXC_506_2')
        self.subject.getCreateNativeInterface('10.07a.3').setDescription('UTOKYO_RX4_2_1')
        self.subject.getCreateNativeInterface('10.07a.4').setDescription('UTOKYO_RX4_2_4')
        self.subject.getCreateNativeInterface('10.08a.5').setDescription('BAD_8A5')
        self.subject.getCreateNativeInterface('10.09a.4').setDescription('BAD_9A4')
        self.subject.getCreateNativeInterface('10.09a.8').setDescription('BAD_9A8')
        self.subject.getCreateNativeInterface('10.11a.5').setDescription('HDXC_1_5_4')
        self.subject.getCreateNativeInterface('10.11a.6').setDescription('OME08_GI1_3')
        self.subject.getCreateNativeInterface('10.11a.7').setDescription('OME08_GI1_4')
        self.subject.getCreateNativeInterface('10.11a.8').setDescription('OME08_GI3_4')
        self.subject.getCreateNativeInterface('10.14a.1').setDescription('DAS3_NODE233')
        self.subject.getCreateNativeInterface('10.14a.2').setDescription('DAS3_NODE234')
        self.subject.getCreateNativeInterface('10.14a.3').setDescription('BAD_14A3')
        self.subject.getCreateNativeInterface('10.14a.4').setDescription('DAS3_NODE235')
        self.subject.getCreateNativeInterface('10.14a.5').setDescription('DAS3_NODE236')
        self.subject.getCreateNativeInterface('10.14a.6').setDescription('BAD_14A6')
        self.subject.getCreateNativeInterface('10.14a.7').setDescription('DAS3_NODE237')
        self.subject.getCreateNativeInterface('10.14a.8').setDescription('DAS3_NODE238')
        self.subject.getCreateNativeInterface('10.15a.1').setDescription('DAS3_UVA')
        self.subject.getCreateNativeInterface('10.15a.2').setDescription('DAS3_UVA_MN')
        self.subject.getCreateNativeInterface('10.15a.6').setDescription('HDXC_508.1.6')
        self.subject.getCreateNativeInterface('10.15a.7').setDescription('HDXC_508.1.7')
        self.subject.getCreateNativeInterface('10.15a.8').setDescription('STARPLANE_HSUM')
        self.subject.getCreateNativeInterface('10.16a.1').setDescription('STARPLANE_1')
        self.subject.getCreateNativeInterface('10.16a.2').setDescription('STARPLANE_2')
        self.subject.getCreateNativeInterface('10.16a.3').setDescription('STARPLANE_3')
        self.subject.getCreateNativeInterface('10.16a.4').setDescription('STARPLEN_4')
        self.subject.getCreateNativeInterface('10.16a.5').setDescription('STARPLANE_5')
        self.subject.getCreateNativeInterface('10.16a.6').setDescription('STARPLANE_6')
        self.subject.getCreateNativeInterface('10.16a.7').setDescription('DAS3_NODE239')
        self.subject.getCreateNativeInterface('10.16a.8').setDescription('DAS3_NODE240')
    
