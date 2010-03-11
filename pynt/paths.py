# -*- coding: utf-8 -*-
"""The pynt.paths module network connections, consisting of multiple hops, and perhaps different layers.
The module is heavily based for use with the algorithm packages, but it should be general. 
(perhaps some things will move back to the algorithms if desired)

In short, these objects are defined:

Path: 
    sequence of Hops

Hop:
    connection point
    connection (from previous hop to this hop)
    stack

Stack:
    sequence of LayerProperties

LayerProperty:
    adaptationfunction
    interfacecount
    layer
    LabelSet
"""

# built-in modules
import types
import UserList
# local modules
import pynt.elements
import pynt.layers


class Direction(object):
    """Direction distinguishes ingress and egress dataflows and is used to prevent an 
    algorithm from switching interface A to interface B, and then forward the data with 
    another switchTo to interface C. While both switchedTo are possible, it is inconsistent 
    with the direction of the dataflow."""
    name = ""
    def __init__(self, name=""):
        self.name = name
    def __str__(self):
        return self.name
    def __repr__(self):
        return "<Direction %s>" % self.name

directionNone       = Direction("None")
directionInternal   = Direction("internal")  # towards the internal of a device: adaptation and switchTo
directionExternal   = Direction("external")  # towards the external of a device: de-adaption and connectedTo


class Hop(object):
    cp = None               # The connection point
    prevconnection  = None  # pointer to the previous connection (between this and the previous item in the path)
    stack           = None  # The adaptation stack so far
    path            = None  # The Path so far, including this last Hop
    metric          = 0.0   # The total metric so far
    def __init__(self, cp, connection, stack, prevpath):
        assert(isinstance(cp, pynt.elements.ConnectionPoint))
        assert(isinstance(connection, Connection))
        assert(isinstance(stack, Stack))
        assert(isinstance(prevpath, Path))
        path = Path(prevpath + [self])
        self.metric = prevpath.getMetric() + connection.getMetric()
        self.cp             = cp
        self.prevconnection = connection
        self.stack          = stack
        self.path           = path
    # def getConnectedHops(self):
    #     pass
    # def getAdaptationStack(self):
    #     pass
    # def getPreviousConnectionType(self):
    #     pass
    def getPreviousConnection(self):
        return self.prevconnection
    def getConnectionPoint(self):
        return self.cp
    def getStack(self):
        return self.stack
    def duplicateStack(self):
        """Copy the stack, so that we don't overwrite the labels of previous interfaces."""
        self.stack = self.stack[:]
        return self.stack
    def getMetric(self):
        return self.metric
    def getPath(self):
        return self.path
    def __str__(self):
        return "<Hop %s>" % self.cp.getURIdentifier()
    def __repr__(self):
        return "<Hop %s>" % self.cp.getURIdentifier()


class Path(UserList.UserList):
    """A Path is simply a list of hops."""
    def getStack(self):
        lasthop = self.getLastHop()
        if lasthop:
            return lasthop.getStack()
        else:
            return Stack()
    def getMetric(self):
        lasthop = self.getLastHop()
        if lasthop:
            return lasthop.getMetric()
        else:
            return 0.0
    def getLastHop(self):
        try:
            return self.data[-1]
        except IndexError:
            return None
    def copy(self):
        """Make a deep copy of the Path, in particular from the LayerProperties in the stack of each Hop.
        This is done so we can modify the properties in the copy, without affecting the parent.
        As a special constraint: if two layerproperties have the same pointer, make sure the 
        pointer remains the same in the copy. The same applies for the stack pointer."""
        stackptrs = {} # old id -> new object
        lpropptrs = {} # old id -> new object
        newpath = Path()
        for hop in self:
            if id(hop.stack) in stackptrs:
                newstack = stackptrs[id(hop.stack)]
            else:
                newstack = self.stackcopy(hop.stack, lpropptrs)
                stackptrs[id(hop.stack)] = newstack
            newhop = Hop(hop.cp, hop.prevconnection, newstack, newpath)
            newpath.append(newhop)
        return newpath
    def stackcopy(self, stack, lpropptrs):
        newstack = Stack()
        for lprop in stack:
            if id(lprop) in lpropptrs:
                newlprop = lpropptrs[id(lprop)]
            else:
                newlprop = lprop.copy()
                lpropptrs[id(lprop)] = newlprop
            newstack.append(newlprop)
        return newstack
    # TODO: override append to verify that all objects are isinstance Hop
    def prettyprint(self):
        for hop in self.data:
            connection  = hop.getPreviousConnection()
            cp          = hop.getConnectionPoint()
            string  = "%40s --> " % connection.getDescription()
            if cp.getDevice():
                string += "%-11s " % cp.getDevice().getName()
            else:
                string += "%-11s " % ""
            string += "%-18s" % cp.getIdentifier()
            interfacetype = type(cp).__name__
            string += "  (%s)" % interfacetype[0].lower()
            #string += "   metric: %6.2f" % hop.getMetric()
            string += "   ext labels: %-12s" % cp.egressLabelSetToStr()
            string += "   int labels: %-12s" % cp.internalLabelSetToStr()
            stack = []
            for elt in hop.getStack():
                # stack.append(elt.adaptationfunction.getName())
                stack.append(elt.getLayer().getName())
                # stack.append("%s" % elt.getEgressLabelSet())
                # stack.append(elt)
            string += "   stack: %s" % (stack)  # TODO: remove .getids()
            print string
    def shortstr(self):
        data = []
        for elt in self.data:
            data.append(elt.getName())
        stack = []
        for elt in self.getStack():
            stack.append(elt.getLayer().getName())
        return "<Path %s metric=%0.2f stack=%s>" % (data, self.getMetric(), stack)
    def __str__(self):
        path = []
        for elt in self.data:
            path.append(elt.getConnectionPoint().getName())
        stack = []
        for elt in self.getStack():
            stack.append(elt.getLayer().getName())
        return "<Path %s metric=%0.2f stack=%s>" % (path, self.getMetric(), stack)



class Stack(UserList.UserList):
    """An adaptation stack. A list of LayerProperties.
    The stack starts with the highest adaptation, down the to lowest layer."""
    def getLastAdaptationFunction(self):
        """Return the adaptation at the lowest layer, or None if there is only one layer"""
        layerprop = self.getLowestLayer()
        if layerprop:
            return layerprop.adaptationfunction
        else:
            return None
    def getLowestLayer(self):
        try:
            return self.data[-1]
        except IndexError:
            return None
    def copy(self):
        """Return a deep copy of the current stack"""
        newstack = Stack()
        for layerprop in self.data:
            newstack.append(layerprop.copy())
        return newstack
    def duplicateLowestLayer(self):
        """Make a (deep) copy of the layer properties of the lowest (=current) layer, 
        so we can safely modify it's values."""
        try:
            layerprop = self.data[-1]
            self.data[-1] = layerprop.copy()
            return self.data[-1]
        except IndexError:
            return None
    def issubset(self, superstack):
        """Value is another stack. Returns True if (labels of) this stack is complete covered by the given stack."""
        assert isinstance(superstack, Stack)
        if len(self) != len(superstack):
            return False
        for i in range(len(self)):
            if not (self[i].issubset(superstack[i])):
                return False
        return True
    def getids(self):
        """debugging only: return a list of id() of the elements"""
        idstack = []
        for elt in self.data:
            idstack.append(id(elt))
        return idstack
    def isempty(self):
        return (len(self.data) <= 1)
    # TODO: override append to verify that all objects are LayerProperty instances
    def __str__(self):
        return "<%s %s at %x>" % (self.__class__.__name__, self.data, id(self))
    def __repr__(self):
        return "<%s %s at %x>" % (self.__class__.__name__, self.data, id(self))

class LayerProperty(pynt.elements.MultiLabelCPMixIn, pynt.elements.MultiPropertyCPMixIn):
    adaptationfunction  = None  # The adaptation from a client layer to this layer
    interfacecount      = 1     # The number of interfaces (for inverse multiplexing)
    layer               = None  # required for the mix-ins
    configurable        = True  # required for the mix-ins
    # The other properties are defined in MultiLabelCPMixIn and MultiPropertyCPMixIn.
    def __init__(self, layer, adaptationfunction, interfacecount=1):
        pynt.elements.MultiLabelCPMixIn.__init__(self)
        pynt.elements.MultiPropertyCPMixIn.__init__(self)
        self.layer = layer
        self.interfacecount = interfacecount
        self.adaptationfunction = adaptationfunction
    def copy(self):
        """return a deep copy of myself, so that we can modify the copy without modifying the original."""
        newlayerprop = LayerProperty(self.layer, self.adaptationfunction, self.interfacecount)
        newlayerprop.setMultiLabelValuesFromCP(self)
        newlayerprop.setMultiPropertyValuesFromCP(self)
        return newlayerprop
    def setvaluesFromCp(self, cp):
        """Based on the connection point, set the values."""
        self.setMultiLabelValuesFromCP(cp)
        self.setMultiPropertyValuesFromCP(cp)
    def getLayer(self):
        return self.layer
    def getInterfaceCount(self):
        return self.interfacecount
    def issubset(self, layerprop):
        """Returns True if (labels of) this layerproperty (self) is complete covered by the given layerproperty."""
        if self.adaptationfunction != layerprop.adaptationfunction:
            return False
        elif self.layer != layerprop.layer:
            return False
        elif self.interfacecount != layerprop.interfacecount:
            return False
        else:
            return self.getLabelSet().issubset(layerprop.getLabelSet())
    def __str__(self):
        return "<LayerProperty layer=%s count=%d adaptation=%s extlabels=%s>" % (self.layer, \
                self.interfacecount, self.adaptationfunction, self.getEgressLabelSet())
    def __repr__(self):
        layername = self.layer and self.layer.getName() or None
        adaptationname = self.adaptationfunction and self.adaptationfunction.getName() or None
        return "<LayerProperty layer=%s count=%d adaptation=%s labels=%s>" % (layername, \
                self.interfacecount, adaptationname, self.getEgressLabelSet())



class Connection(object):
    """A connection between two hops. Either an adaptation, link, broadcast segement or switch matrix"""
    direction       = directionNone
    nextdirection   = directionNone
    metric          = 1.0 ## 0.0 # The metric of this connection only
    # TODO: use __str__ insteead of getDescription?
    def getDescription(self):
        return "Unkown"
    def setMetric(self, metric=0.0):
        self.metric = metric
    def getMetric(self):
        return self.metric


class StartingPoint(Connection):
    """The "connection" before the first hop in a path."""
    direction       = directionNone
    nextdirection   = [directionExternal,directionInternal]
    metric          = 0.0 # The metric of this connection only
    def getDescription(self):
        return "Starting point"


class AdaptationConnection(Connection):
    direction       = directionExternal
    nextdirection   = [directionExternal]
    metric          = 1.0 ## 0.0 # The metric of this connection only
    adaptationfunction = None
    def __init__(self, adaptationfunction):
        assert(isinstance(adaptationfunction, pynt.layers.AdaptationFunction))
        self.adaptationfunction = adaptationfunction
    def getDescription(self):
        return "Adaptation %s" % self.adaptationfunction.getName()


class DeAdaptationConnection(Connection):
    direction       = directionInternal
    nextdirection   = [directionInternal]
    metric          = 1.0 ## 0.0 # The metric of this connection only
    adaptationfunction = None
    def __init__(self, adaptationfunction):
        assert(isinstance(adaptationfunction, pynt.layers.AdaptationFunction))
        self.adaptationfunction = adaptationfunction
    def getDescription(self):
        return "De-adaptation %s" % self.adaptationfunction.getName()


class SwitchToConnection(Connection):
    direction       = directionInternal
    nextdirection   = [directionExternal]
    metric          = 1.0 ## 1.1 # The metric of this connection only
    def getDescription(self):
        return "Switch to (internal connection)"


class SwitchMatrixConnection(SwitchToConnection):
    switchmatrix    = None
    def __init__(self, switchmatrix):
        assert(isinstance(switchmatrix, pynt.elements.SwitchMatrix))
        self.switchmatrix = switchmatrix
    def getDescription(self):
        return "Through %s" % self.switchmatrix.getName()


class PacketSwitchToConnection(SwitchToConnection):
    pass


class CircuitSwitchToConnection(SwitchToConnection):
    pass


class BroadcastSwitchToConnection(SwitchToConnection):
    pass


class ConnectedToConnection(Connection):
    direction       = directionExternal
    nextdirection   = [directionInternal]
    metric          = 1.0 # The metric of this connection only
    def getDescription(self):
        return "Connection"


class LinkToConnection(ConnectedToConnection):
    metric          = 1.0 # The metric of this connection only
    segment         = None  # None or a broadcast segment
    def __init__(self, segment=None):
        assert(isinstance(segment, (types.NoneType, pynt.elements.BroadcastSegment)))
        self.segment = segment
    def getDescription(self):
        if self.segment:
            return "Link through broadcast segment %s" % self.segment.getName()
        else:
            return "Link to"


class BroadcastSegmentConnection(LinkToConnection):
    segment         = None
    def __init__(self, segment):
        assert(isinstance(segment, pynt.elements.BroadcastSegment))
        self.segment = segment
    def getDescription(self):
        return "Link through broadcast segment %s" % self.segment.getName()


class LinkConnection(BroadcastSegmentConnection):
    pass

