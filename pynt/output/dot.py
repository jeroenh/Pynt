# -*- coding: utf-8 -*-
"""Output module to generate GraphViz dot files, as described at 
http://www.graphviz.org/doc/info/lang.html and http://www.graphviz.org/doc/info/attrs.html"""

import random
import pynt.output
import pynt.paths
import pynt.technologies
import math

# TODO: 
# - use penWidth instead of setlinewidth
# - use doubleellipse or simular for potentialinterfaces


class DeviceGraphOutput(pynt.output.BaseOutput):
    """Output to the GraphViz Dot format. Each Device is mapped to a vertex."""
    
    def __init__(self, outfile=None, subject=None, atomic=True):
        pynt.output.BaseOutput.__init__(self,outfile=outfile,subject=subject)
        self.indent = 0
        self._unconfirmedConnections = []
        self._printInterfaceLabels = True
    
    def write(self, string):
        self.outfile.write((self.indent*'    ')+str(string)+"\n")
    
    def printHeader(self):
        self.write('graph RDFS {')
        self.indent += 1
        self.write('rankdir=LR;')
        self.write('ranksep="1.2";')
        self.write('edge [arrowhead=none];')
        self.write('node [label="\N", fontname=Arial, fixedsize=false, color=lightblue,style=filled];')
    
    def printFooter(self):
        for interface, connectedInterface in self._unconfirmedConnections:
            head = ""
            tail = ""
            labels = ["style=dashed"]
            if isinstance(interface, pynt.elements.BroadcastSegment):
                head = interface.getName()
            elif isinstance(interface, pynt.elements.Interface):
                head = interface.getDevice().getName()
                labels.append('headlabel="'+interface.getName()+'"')
            if isinstance(connectedInterface, pynt.elements.Interface):
                if connectedInterface.getDevice():
                    tail = connectedInterface.getDevice().getName()
                    labels.append('taillabel="'+ connectedInterface.getName()+'"')
            elif isinstance(connectedInterface, pynt.elements.BroadcastSegment):
                tail = connectedInterface.getName()
            # TODO: fix this in a more clean way.
            # Ignore stub networks for now, they pollute the graph.
            if not tail.startswith("Stub"):
                self.write('"%s" -- "%s" [%s];' % (tail, head, ", ".join(labels)))
        self.indent -= 1
        self.write("}\n")
    
    def printDevice(self, device):
        self.write('"%s";' % device.getName())
    
    def printBroadcastSegment(self, bc):
        # TODO: fix this in a more clean way.
        # Ignore stub networks for now, they pollute the graph.
        if not bc.getName().startswith("Stub"):
            self.write('"%s" [shape=octagon];' % bc.getName())
            # After printing the node, we must also print the connection
            # or add it to the unconfirmed connections.
            for connectedInterface in bc.getConnectedInterfaces():
                if (connectedInterface, bc) in self._unconfirmedConnections:
                    head = ""
                    tail = bc.getName()
                    labels = []
                    self._unconfirmedConnections.remove((connectedInterface, bc))
                    if isinstance(connectedInterface, pynt.elements.Interface):
                        headdevice = connectedInterface.getDevice()
                        if headdevice != None:
                            head = headdevice.getName()
                        else:
                            head = connectedInterface.getName()
                        labels.append('headlabel="'+connectedInterface.getName()+'"')
                    if not head or not tail:
                        raise Exception("BCSegment (%s) is connected to %s which is not an interface" % (bc, connectedInterface))
                    if connectedInterface.getLayer() == pynt.technologies.ip.GetLayer("ip"):
                        labels.append('style="setlinewidth(%s)"' % self.metricToLineWidth(connectedInterface,bc))
                    self.write('"%s" -- "%s" [%s];' % (tail, head, ", ".join(labels)))
                else:
                    self._unconfirmedConnections.append((bc,connectedInterface))

    def printInterface(self, interface):
        for connectedInterface in interface.getConnectedInterfacesOnly():
            if (connectedInterface, interface) in self._unconfirmedConnections:
                head = ""
                tail = ""
                labels = []
                self._unconfirmedConnections.remove((connectedInterface, interface))
                if isinstance(interface, pynt.elements.Interface):
                    headdevice = interface.getDevice()
                    if headdevice != None:
                        head = headdevice.getName()
                    else:
                        head = interface.getName()
                    if self._printInterfaceLabels:
                        labels.append('headlabel="'+interface.getName()+'"')
                if isinstance(connectedInterface, pynt.elements.Interface):
                    taildevice = connectedInterface.getDevice()
                    if taildevice != None:
                        tail = taildevice.getName()
                    else:
                        tail = interface.getName()
                    if self._printInterfaceLabels:
                        labels.append('taillabel="'+ connectedInterface.getName()+'"')
                elif isinstance(connectedInterface, pynt.elements.BroadcastSegment):
                    tail = connectedInterface.getName()
                if not head or not tail:
                    raise Exception("Can't make heads or tails of this (%s,%s)" % (interface,connectedInterface))
                if interface.getMetric() and hasattr(connectedInterface, "getMetric") and connectedInterface.getMetric():
                    labels.append('style="setlinewidth(%s)"' % self.metricToLineWidth(interface, connectedInterface))
                if interface.getCapacity() and (interface.getCapacity() > interface.getAvailableCapacity()):
                    labels.append('color="#ff0000"')
                if not tail.startswith("Stub"):
                    self.write('"%s" -- "%s" [%s];' % (tail, head, ", ".join(labels)))
            else:
                self._unconfirmedConnections.append((interface,connectedInterface))
    
    def metricToLineWidth(self, *args):
        metric = 0
        for intf in args:
            if isinstance(intf, pynt.elements.BroadcastSegment):
                metric += 1
            elif isinstance(intf, pynt.elements.Interface) and intf.getMetric():
                metric += intf.getMetric()
        if metric:
            if metric > 100:
                return 1
            else:
                # The function below has the following properties:
                # f(2) = 10
                # f(4) = 7
                # f(10) = 4
                # f>57 = 1
                # (and when f is bigger than 100, it becomes 0)
                return int((15*math.sqrt(metric))/metric)
        else:
            return 1

    def printLocation(self, loc):
        pass
    
    def printAdminDomain(self, dom):
        pass


class InterfaceGraphOutput(pynt.output.BaseOutput):
    """Output to the GraphViz Dot format. Each Interface and each SwitchMatrix is mapped to a vertex,
    external links (linkTo, connectedTo, broadcastsegment), internal links (switchTo) and 
    adaptations are mapped to edges. The graphical convention is:
    * Devices: subgraphs (squares with vertices)
    * Interfaces: ellipse, possible with colour representing the layer
    * Switch Matrices: diamond, possible with colour representing the layer
    * linkTo, connectedTo: directed edge with open arrow
    * adaptation: directed edge with empty arrow
    * de-adaptation: directed edge with invempty arrow
    * switchTo: directed edge with diamond arrow
    * part of switch matrix: *uni*directed edge with odiamond arrows (in both directions)
    """
    
    def __init__(self, outfile=None, subject=None, atomic=True):
        pynt.output.BaseOutput.__init__(self,outfile=outfile,subject=subject)
        self.indent = 0
        self.layercolor = {}  # layer -> color ID
    
    def getNewColor(self, index):
        """Return a color name. Index is 0-based.
        This product includes color specifications and designs developed by Cynthia Brewer (http://colorbrewer.org/)."""
        # Suggested schemas as shown at http://www.graphviz.org/doc/info/colors.html:
        accent8  = ["#7fc97f", "#beaed4", "#fdc086", "#ffff99", "#386cb0", "#f0027f", "#bf5b17", "##666666"]
        paired12 = ["#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f"]
        pastel19 = ["#fbb4ae", "#b3cde3", "#ccebc5", "#decbe4", "#fed9a6", "#ffffcc", "#e5d8bd", "#fddaec", "#f2f2f2"]
        dark28   = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d", "#666666"]
        rdylbu11 = ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee090", "#ffffbf", "#e0f3f8", "#abd9e9", "#74add1", "#4575b4", "#313695"]
        set19    = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33", "#a65628", "#f781bf", "#999999"]
        set28    = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"]
        set312   = ["#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd", "#ccebc5", "#ffed6f"]
        spectral11 = ["#9e0142", "#d53e4f", "#f46d43", "#fdae61", "#fee08b", "#ffffbf", "#e6f598", "#abdda4", "#66c2a5", "#3288bd", "#5e4fa2"]
        schema = set312
        try:
            return "%s" % (schema[index])
        except IndexError:
            return "#%02x%02x%02x" % (random.randint(0,255),random.randint(0,255), random.randint(0,255))
    
    def getLayerColor(self, layer):
        if layer not in self.layercolor:
            self.layercolor[layer] = self.getNewColor(len(self.layercolor))
        return self.layercolor[layer]
    
    def write(self, string):
        self.outfile.write((self.indent*'    ')+str(string)+"\n")
    
    def printHeader(self):
        self.write('digraph INTERFACERDF {')
        self.indent += 1
        #self.write('rankdir=LR;')
        #self.write('ranksep="1.2";')
        self.write('edge [arrowhead=open];')
        self.write('node [fontname=Helvetica,fixedsize=false,color=lightblue,style=filled];')
        
    
    def printFooter(self):
        self.indent -= 1
        self.write("}\n")
    
    def printDevice(self, device):
        self.write('subgraph "cluster%s" {' % device.getIdentifier())
        self.indent += 1
        self.write('label="%s"; fontsize=30;' % device.getName())
        self.write('"hidden%s"  [ label="", shape=none, width=0, height=0 ];' % device.getIdentifier())
        for interface in device.getLogicalInterfaces():
            self.write('"%s" [label="%s", fillcolor="%s", availablechannels="%s"];' % \
                    (interface.getURIdentifier(), interface.getName(), \
                    self.getLayerColor(interface.getLayer()), interface.getInternalLabelSet()))
        for switchmatrix in device.getSwitchMatrices():
            self.write('"%s" [label="%s", shape=diamond, fillcolor="%s"];' % \
                    (switchmatrix.getURIdentifier(), switchmatrix.getName(), \
                    self.getLayerColor(switchmatrix.getLayer())))
        self.indent -= 1
        self.write('}')
    
    def printBroadcastSegment(self, bc):
        # TODO: fix this in a more clean way.
        # Ignore stub networks for now, they pollute the graph.
        if not bc.getName().startswith("Stub"):
            self.write('"%s" [shape=octagon];' % bc.getName())
    
    def printInterface(self, interface):
        # * linkTo, connectedTo: directed edge with open arrow
        for peer in interface.getConnectedInterfaces(): # including link to
            self.write('"%s" -> "%s" [arrowhead=open];' % (interface.getURIdentifier(), peer.getURIdentifier()))
        # * adaptation: directed edge with empty arrow
        for (peer,adaptationfunction) in interface.getAllServerTuples():
            self.write('"%s" -> "%s" [arrowhead=empty, label="%s", adaptation="%s"];' % (interface.getURIdentifier(), peer.getURIdentifier(), adaptationfunction.getName(), adaptationfunction.getURIdentifier()))
        # * de-adaptation: directed edge with invempty arrow
        for (peer,adaptationfunction) in interface.getAllClientTuples():
            self.write('"%s" -> "%s" [arrowhead=invempty, adaptation="%s"];' % (interface.getURIdentifier(), peer.getURIdentifier(), adaptationfunction.getURIdentifier()))
        # * part of switch matrix: *uni*directed edge with odiamond arrows (in both directions)
        # * switchTo: directed edge with diamond arrow
        switchmatrix = interface.getSwitchMatrix()
        if switchmatrix:
            self.write('"%s" -> "%s" [dir=both, arrowtail=diamond, arrowhead=odiamond];' % (interface.getURIdentifier(), switchmatrix.getURIdentifier()))
            for peer in switchmatrix.getActualSwitchedInterfaces(interface):
                self.write('"%s" -> "%s" [arrowhead=diamond];' % (interface.getURIdentifier(), peer.getURIdentifier()))
        else:
            for peer in interface.getActualSwitchedInterfaces():
                self.write('"%s" -> "%s" [arrowhead=diamond];' % (interface.getURIdentifier(), peer.getURIdentifier()))
    
    def printLocation(self, loc):
        pass
    
    def printAdminDomain(self, dom):
        pass

class DomainGraphOutput(DeviceGraphOutput):
    def __init__(self, outfile=None, subject=None, atomic=True):
        DeviceGraphOutput.__init__(self, outfile, subject, atomic)
        self.domains = {}
        
    def addDeviceDomain(self, device):
        dom = device.getDomain()
        if dom:
            if self.domains.has_key(dom):
                self.domains[dom].append(device.getName())
            else:
                self.domains[dom] = [device.getName()]
            
    def printDevice(self, device):
        if device.getDomain():
            self.addDeviceDomain(device)
        else:
            self.write('"%s";' % device.getName())
        
        for intf in device.getNativeInterfaces():
            self.printInterface(intf)

    def printFooter(self):
        for interface, connectedInterface in self._unconfirmedConnections:
            head = ""
            tail = ""
            labels = ["style=dashed"]
            if isinstance(interface, pynt.elements.BroadcastSegment):
                head = interface.getName()
            elif isinstance(interface, pynt.elements.Interface):
                head = interface.getDevice().getName()
                labels.append('headlabel="'+interface.getName()+'"')
            if isinstance(connectedInterface, pynt.elements.Interface):
                tail = connectedInterface.getDevice().getName()
                labels.append('taillabel="'+ connectedInterface.getName()+'"')
            elif isinstance(connectedInterface, pynt.elements.BroadcastSegment):
                tail = connectedInterface.getName()
            # TODO: fix this in a more clean way.
            # Ignore stub networks for now, they pollute the graph.
            if not tail.startswith("Stub"):
                self.write('"%s" -- "%s" [%s];' % (tail, head, ", ".join(labels)))
        for dom in self.domains:
            self.write('subgraph cluster%s {' % dom)
            self.indent += 1
            for dev in self.domains[dom]:
                self.write('"%s";' % dev)
            self.indent -= 1
            self.write('}')
        self.indent -= 1
        self.write("}\n")
        
class ProgressDotOutput(InterfaceGraphOutput):
    count = 0
    path  = None
    color = "#ffffff"
    networkType = ""

    def inPath(self, interface1, interface2, connectiontype):
        """Return True if the connection from interface1 to interface2 is part of self.path"""
        if (not self.path) or (len(self.path) <= 1):
            return 0
        count = 0
        for hop in range(1,len(self.path)):
            if (self.path[hop-1].cp == interface1) and \
                    (self.path[hop].cp == interface2) and \
                    isinstance(self.path[hop].prevconnection, connectiontype):
                count += 1
        return count

    def inPathSwitchMatrix(self, interface):
        """Return True if the connection from interface to the previous or the next goes to a switch matrix"""
        if (not self.path) or (len(self.path) <= 1):
            return 0
        count = 0
        for hop in range(1,len(self.path)):
            # Look to see if this interface is in the path
            if (self.path[hop-1].cp == interface): 
                # Is the switch matrix of this interface the same of the
                # next interface
                if (interface.getSwitchMatrix() ==  self.path[hop].cp.getSwitchMatrix()):
                    count += 1
                # Now, we need to draw 'backward', so:
                # Was the switchmatrix of this interface the same of the
                # preceding interface? 
                if (interface.getSwitchMatrix() == self.path[hop-2].cp.getSwitchMatrix()):
                    count += 1
        return count

    def printHeader(self):
        super(ProgressDotOutput, self).printHeader()
        #if self.count:
        #    self.write('"counter_label" [label="%s", fontsize=40];' % (self.count))

    def getStyle(self, basestyle, inpathcount, colour):
        """Return the dot style for a link which is inpathcount number of times part of the path.
        Colour is only used if inpathcount > 0"""
        if inpathcount > 0:
            basestyle += ', color="%s", style="setlinewidth(%d)"' % (colour, -1+4*inpathcount)
        return basestyle

    def printInterface(self, interface):
        """Note: printInterface prints the edges in the dot file. 
        The interfaces itself are printed in printDevice, so interfaces without devices are never printed; 
        yes, that's a bug.)"""
        # * linkTo, connectedTo: directed edge with open arrow
        for peer in interface.getConnectedInterfaces(): # including link to
            inpathcount = self.inPath(interface, peer, pynt.paths.ConnectedToConnection)
            style = self.getStyle("arrowhead=open", inpathcount, self.color)
            self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), peer.getURIdentifier(), style))
        # * adaptation: directed edge with empty arrow
        for (peer,adaptationfunction) in interface.getAllServerTuples():
            inpathcount = self.inPath(interface, peer, pynt.paths.AdaptationConnection)
            style = 'arrowhead=empty, label="%s", adaptation="%s"' % (adaptationfunction.getName(), adaptationfunction.getURIdentifier())
            style = self.getStyle(style, inpathcount, self.color)
            self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), peer.getURIdentifier(), style))
        # * de-adaptation: directed edge with invempty arrow
        for (peer,adaptationfunction) in interface.getAllClientTuples():
            inpathcount = self.inPath(interface, peer, pynt.paths.DeAdaptationConnection)
            style = 'arrowhead=invempty, adaptation="%s"' % (adaptationfunction.getURIdentifier())
            style = self.getStyle(style, inpathcount, self.color)
            self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), peer.getURIdentifier(), style))
        # * part of switch matrix: *uni*directed edge with odiamond arrows (in both directions)
        # * switchTo: directed edge with diamond arrow
        switchmatrix = interface.getSwitchMatrix()
        if switchmatrix:
            # I would have expected to see non empty values in the list returned by:
            # switchmatrix.getActualSwitchedInterfaces(interface)
            # interface.getDirectlySwitchedInterfaces()
            # but it is not. So I use the following function to see if the path needs to be colored
            inpathcount = self.inPathSwitchMatrix(interface)
            style = 'dir=both, arrowtail=diamond, arrowhead=odiamond'
            style = self.getStyle(style, inpathcount, self.color)
            self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), switchmatrix.getURIdentifier(), style))
        else: 
            for peer in interface.getActualSwitchedInterfaces():
                inpathcount = self.inPath(interface,peer,pynt.paths.SwitchToConnection)
                style = 'arrowhead=diamond'
                style = self.getStyle(style, inpathcount, self.color)
                self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), peer.getURIdentifier(), style))

    def printFooter(self):
        # self.write('"network_name_label" [label="%s", fontsize=40];' % (self.networkType))
        if self.networkType in ["glif", "glifalt"]:
            self.write('hiddenManLanDevice -> hiddenCANetDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenStarLightDevice -> hiddenCANetDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenStarLightDevice -> hiddenManLanDevice [ weight=100, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenManLanDevice -> hiddenNetherLightDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenUvADevice -> hiddenNetherLightDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenQuebecEthernetDevice -> hiddenCANetDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
        self.indent -= 1
        self.write("}")

    def setNetworkType(self, network):
        self.networkType = network

