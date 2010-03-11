# -*- coding: utf-8 -*-
"""The pynt.elements module defines a few abstract network element classes: Device, Interface and Blade"""

# built-in modules
import logging
# local modules
import pynt
import pynt.xmlns
import pynt.rangeset
import pynt.layers
import pynt.logger


class NetworkElement(pynt.xmlns.RDFObject):
    """A network element; an RDF object representing a part of a physical network."""
    def __init__(self, identifier, namespace):
        # WARNING: A RDFObject should always be created using a [Get]CreateRDFObject() function
        # The init function must never create any other RDFObjects, even not indirectly
        pynt.xmlns.RDFObject.__init__(self, identifier=identifier, namespace=namespace)
        self.location = None
        pynt.logger.InitLogger()
        self.logger = logging.getLogger("pynt.elements")
    
    def setLocatedAt(self, location):   self.location = location
    def getLocatedAt(self):             return self.location


# TYPES OF CONNECTION POINTS:
# 
# ConnectionPoint               All Connection Points. An abstract thing representing a logical interface
#    Interface                  All actual Connection Points. It has a label a properties associated with it.
#        StaticInterface        An interface with fixed properties. Can not change. E.g. a laser at 1310 nm.
#        ConfigurableInterface  An interface whose properties can change. E.g. a tunable laser at 1310, which 
#                               can also send at 1300..1500nm
#        MultiplexInterface     Instantiation of a PotentialInterface. E.g. a Tagged VLAN channel
#    PotentialMuxInterface      A virtual (not-instantiated) Interface. It's existance means that one or more 
#                               MultiplexInterface can be created on the fly.
#
# For the language lawers: You may be inclined to define a MultiInterfaceList (an efficient represention of a 
# list of interfaces, with only different labels) as some kind of mix between a PotentialMuxInterface and 
# MultiplexInterface. Well, we don't allow you. If you want that, you need to define another structure.
# You may do this under ConnectionPoint, but not under Interface or PotentialMuxInterface.

class ConnectionPoint(NetworkElement):
    """A connection point or list of related connection points: : a logical interface at a certain layer
    
    Note if you want to create an Interface, use GetCreateConnectionPoint or 
    use the getCreateNativeInterface function of the relevant device."""
    prefix              = ""    # string                           TODO: get rid of these?
    blade               = 0     # int                              TODO: get rid of these?
    port                = 0     # int                              TODO: get rid of these?
    metric              = None
    teaddress           = None
    layer               = None  # Layer object or None (unknown)
    device              = None  # parent device or None (unknown)
    
    actual              = False # signifies that the CP has actual values associated with it. Opposite of potential.
    removable           = False # signifies that the CP may be marked as configued, and can be removed.
    configurable        = False # signifies that the CP has multiple values, one of them that can be picked.
    potential           = False # signifies that the CP is not "real", but one or more can be instantiated. Opposite of actual.
    ismultiple          = False # True if this one object (can) represent(s) multiple connection points
    
    capacity                = None  # float (in Mbyte/s) or None (unknown)
    maximumReservableCapacity = None
    minimumReservableCapacity = None
    granularity               = None
    
    #                       actual      removable  configurable  potential  ismultiple
    # Interface               +           -           ?           -           -
    # StaticInterface         +           -           -           -           -
    # ConfigurableInterface   +           -           +           -           -
    # PotentialInterface      -           ?           +           +           -
    # InstantiatedInterface   +           +           -           -           -
    
    clientadaptations   = None  # dict of adaptation instances, indexed by AdaptationFunction. 
    serveradaptations   = None  # dict of adaptation instances, indexed by AdaptationFunction. 
    # Only one interface in the list of adaptations may point to actual (non-potential) interfaces.
    
    linkedInterfaces    = None  # list of linkTo interfaces (currently: one at most)
    linkedSegment       = None  # linkTo broadcast segment
    connectedInterfaces = None  # connectedTo interfaces (excluding linked interfaces)
    switchedInterfaces  = None  # switchedTo interfaces (excluding packetSwitched and circuitSwitched interfaces)
    packetSwtInterfaces = None  # packetSwitchedTo interfaces
    circuitSwtInterfaces = None # circuitSwitchedTo interfaces
    switchmatrix        = None  # switchmatrix (for now, only one.)

    properties          = None  # mapping of proptypes to propvalues
    
    def __init__(self, identifier, namespace):
        # WARNING: A RDFObject should always be created using a [Get]CreateRDFObject() function
        # The init function must never create any other RDFObjects, even not indirectly
        NetworkElement.__init__(self, identifier=identifier, namespace=namespace)
        # list of interfaces. We MUST create the new lists here, not above, otherwise
        # each interface will share the same list instance.
        self.clientadaptations   = {}   # adaptation towards the client layer (towards the internal switchmatrix)
        self.serveradaptations   = {}   # adaptation towards the server layer (towards the external linkTo)
        self.linkedInterfaces    = []  # linkTo interfaces
        self.linkedSegment       = None  # linkTo broadcast segment
        self.connectedInterfaces = []  # connectedTo interfaces
        self.switchedInterfaces  = []  # switchedTo interfaces
        self.packetSwtInterfaces = []  # packetSwitchedTo interfaces
        self.circuitSwtInterfaces = []  # circuitSwitchedTo interfaces
        self.switchFromInterfaces = []  # sources of switchedTo with self as sink
        self.namespace.networkschema = True
        self.properties = {}
        self.switchmatrix = None
    
    def isConfigured(self):                         return self.removable
    def isPotential(self):                          return self.potential
    
    def setPrefix(self,prefix):                     self.prefix   = str(prefix)
    def setBlade(self,blade):                       self.blade    = int(blade)
    def setPort(self,port):                         self.port     = int(port)
    def setMetric(self,metric):                     self.metric = int(metric)
    def setTEAddress(self, teaddress):              self.teaddress = teaddress
    def setCapacity(self, capacity):                self.capacity       = float(capacity)
    def setMaximumReservableCapacity(self,maximumReservableCapacity):   self.maximumReservableCapacity = float(maximumReservableCapacity)
    def setMinimumReservableCapacity(self,minimumReservableCapacity):   self.minimumReservableCapacity = float(minimumReservableCapacity)
    def setGranularity(self,granularity):           self.granularity = float(granularity)
    
    def setLayer(self,layer):
        assert(isinstance(layer, pynt.layers.Layer))
        self.layer = layer
        # TODO: check if labels and labelsets are allowed with this new layer.
        # TODO: check if layer used to be something different.
    def setDevice(self, device):
        if self.device:
            device.removeLogicalInterface(self)
        self.device = device
        device.addLogicalInterface(self)
    def getPrefix(self):                            return self.prefix
    def getBlade(self):                             return self.blade
    def getPort(self):                              return self.port
    def getMetric(self):                            return self.metric
    def getTEAddress(self):                         return self.teaddress
    def getCapacity(self):                          return self.capacity
    def getMaximumReservableCapacity(self):         return self.maximumReservableCapacity
    def getMinimumReservableCapacity(self):         return self.minimumReservableCapacity
    def getGranularity(self):                       return self.granularity
    def getLayer(self):                             return self.layer
    def getDevice(self):                            return self.device
    def getDeviceIdentifier(self):
        if self.device:
            return self.device.getIdentifier()
        else:
            return None

    def addProperty(self, identifier, value):
        """Set the property type to the property value in the property dict"""
        if not self.layer:
            self.logger.warning("Connection point %s has no layer set. Property %s was not set." % (self.getURIdentifier(), identifier))
            return
        if not self.layer.hasProperty(identifier):
            self.logger.warning("Layer %s for connection point %s does not define property %s, not setting it." % (self.layer.getName(), self.getURIdentifier(), identifier))
            return
        # Does the property already exist in the list? What do we do if it was already added?
        try: # if the class was not initialized properly
            if str(identifier) in self.properties.keys():
                self.logger.warning("Property %s already defined for %s, ignoring property" % (identifier, self.getURIdentifier()))
                return
        except AttributeError:
            self.logger.warning("Properties attribute on %s not defined. Is the class properly initialized?" % self.getURIdentifier())
            return
        # for reference: type of objectvalue is either rdflib.Literal.Literal or rdflib.URIRef.URIRef 
        # FIXME: check for property existing for layer
        self.logger.debug("Setting property for %s to %s" % (identifier, value))
        self.properties[str(identifier)] = value
    def getProperty(self, identifier):
        """Looks for the identifier (for example egressStatus) in the list of
           properties and returns the value for the property. There are two
           assumptions here:
           (1) Properties set on a connectionpoint instance are always layer
               related properties
           (2) An identifier is unique so it will be in the list only once.
           
           See pynt.layers.Layer for more information on how properties are
           handled."""
        if identifier in self.properties.keys():
            return self.properties[identifier]
        else:
            return None
    def getPropertyOptimalRange(self, identifier):
        """Return the optimal values for the property. If not set or the property 
           does not exist, (None, None) is returned."""
        if identifier in self.properties.keys():
            return self.layer.getProperty(identifier).getOptimalRange()
        return (None, None)

    def getProperties(self):
        return self.properties
    
    def addClientInterface(self, interface, adaptationfunction):
        """Add a logical interface as a channel to the current interface"""
        assert(isinstance(adaptationfunction, pynt.layers.AdaptationFunction))
        assert(isinstance(interface, ConnectionPoint))
        if adaptationfunction in self.clientadaptations:
            adaptation = self.clientadaptations[adaptationfunction]
        elif adaptationfunction in interface.serveradaptations:
            adaptation = interface.serveradaptations[adaptationfunction]
        else:
            adaptation = Adaptation(adaptationfunction)
        # Check is redundant; it is already checked (Error "Can't adapt <interface> in <self>: It is already adapted with <self>")
        #if self.isPotential():
        #    for (otherpotential,otheradaptation) in interface.getPotentialServerTuples():
        #        if (self == otherpotential) and (adaptationfunction != otheradaptation):
        #            raise pynt.ConsistencyException(("Two adaptations, %s and %s point to the same potential interface, %s. " \
        #                    "This is not (yet) supported.") % (adaptationfunction.getName(), otheradaptation.getName(), self.getName()))
        #if interface.isPotential():
        #    for (otherpotential,otheradaptation) in self.getPotentialClientTuples():
        #        if (interface == otherpotential) and (adaptationfunction != otheradaptation):
        #            raise pynt.ConsistencyException(("Two adaptations, %s and %s point to the same potential interface, %s. " \
        #                    "This is not (yet) supported.") % (adaptationfunction.getName(), otheradaptation.getName(), interface.getName()))
        ## verify that there is only one adaptation with actual interfaces
        currentAdaptation = self.getClientAdaptation()
        if currentAdaptation not in [None, adaptation]:
            raise pynt.ConsistencyException("Can't adapt %s in %s: It is already adapted with %s." \
                    % (interface.getName(), self.getName(), currentAdaptation))
        currentAdaptation = interface.getServerAdaptation()
        if currentAdaptation not in [None, adaptation]:
            raise pynt.ConsistencyException("Can't adapt %s in %s: It already adapts %s." \
                    % (interface.getName(), self.getName(), currentAdaptation))
        adaptation.addServerInterface(self)
        adaptation.addClientInterface(interface)
        self.clientadaptations[adaptationfunction] = adaptation
        interface.serveradaptations[adaptationfunction] = adaptation
        #print "-> created adaptation %s" % adaptation
    def removeClientInterface(self, interface, adaptationfunction):
        """Remove a logical interface as a channel from the current interace"""
        # TODO: test this code.
        assert(isinstance(adaptationfunction, pynt.layers.AdaptationFunction))
        assert(isinstance(interface, ConnectionPoint))
        # The following may raise a KeyError; we assume the adaptation is defined in both interfaces.
        adaptation = self.clientadaptations[adaptationfunction]
        assert(adaptation == interface.clientadaptations[adaptationfunction])
        # Note that we should either remove self and/or interface from the adaptation.
        # Thus not just remove interface. We remove both, unless there are still other 
        # client resp. server interfaces in the adaptation.
        removeclient = (adaptation.allServerInterfaceCount() <= 1)
        removeserver = (adaptation.allClientInterfaceCount() <= 1)
        if removeclient:
            adaptation.removeClientInterface(interface)
            del interface.serveradaptations[adaptationfunction]
        if removeserver:
            adaptation.removeServerInterface(self)
            del self.clientadaptations[adaptationfunction]
        # If all went well, we have no dangling adaptations.
        assert(adaptation.allServerInterfaceCount() + adaptation.allClientInterfaceCount() != 1)
    def addServerInterface(self, interface, adaptationfunction):
        """Add an a logical interface that embeds data of this interface, building an external adaptation stack"""
        interface.addClientInterface(self, adaptationfunction)
    def removeServerInterface(self, interface, adaptationfunction):
        """Remove a server layer interface from this interface"""
        interface.removeClientInterface(self, adaptationfunction)
    
    def getClientAdaptation(self):
        """Return the actual adaptation that is currently configured; skipping any potential adaptations."""
        for adaptation in self.clientadaptations.values():
            if adaptation.hasActualClients():
                return adaptation
        return None
    def getClientAdaptationFunction(self):
        """Return the actual configured adaptation function; skipping any potential adaptations."""
        for adaptation in self.clientadaptations.values():
            if adaptation.hasActualClients():
                return adaptation.function
        return None
    def getClientInterfaces(self):
        """Return the actual client interfaces, excluding any potential interfaces"""
        for adaptation in self.clientadaptations.values():
            if adaptation.hasActualClients(): # we assume only one adaptation can have client interfaces
                return adaptation.getClientInterfaces()
        return []
    def getAllClientTuples(self):
        """Return a full list of (interface, adaptation) tuplets of client layer interfaces. 
        Both actual and potential interfaces."""
        interfaces = []
        for adaptation in self.clientadaptations.values():
            if adaptation.potentialclient:
                interfaces.append((adaptation.potentialclient, adaptation.function))
            for client in adaptation.clients:
                interfaces.append((client, adaptation.function))
        return interfaces
    def getPotentialClientTuples(self):
        """Return a list of (interface, adaptation) tuplets for all client layer potential interfaces."""
        interfaces = []
        for adaptation in self.clientadaptations.values():
            if adaptation.potentialclient:
                interfaces.append((adaptation.potentialclient, adaptation.function))
        return interfaces
    def getClientStackInterfaces(self, curlist=None):
        """Recursively fetch all client layer interfaces, building a full stack of channels"""
        if curlist == None:
            curlist = []
        # depth first tree search with duplicate elimination
        for (interface,adaptation) in self.getAllClientTuples():
            if interface in curlist:
                continue
            curlist.append(interface)
            interface.getClientStackInterfaces(curlist)
        return curlist
    
    def getServerAdaptation(self):
        """Return the adaptation function that is currently configured; skipping any potential adaptations."""
        for adaptation in self.serveradaptations.values():
            if adaptation.hasActualServers():
                return adaptation
        return None
    def getServerAdaptationFunction(self):
        """Return the adaptation function that is currently configured; skipping any potential adaptations."""
        for adaptation in self.serveradaptations.values():
            if adaptation.hasActualServers():
                return adaptation.function
        return None
    def getServerInterfaces(self):
        for adaptation in self.serveradaptations.values():
            if adaptation.hasActualServers():
                return adaptation.getServerInterfaces()
        return []
    def getAllServerTuples(self):
        """Return a full list of (interface, adaptationfunction) tuplets of server layer interfaces. 
        Both actual and potential interfaces."""
        interfaces = []
        for adaptation in self.serveradaptations.values():
            if adaptation.potentialserver:
                interfaces.append((adaptation.potentialserver, adaptation.function))
            for server in adaptation.servers:
                interfaces.append((server, adaptation.function))
        return interfaces
    def getPotentialServerTuples(self):
        """Return a list of (interface, adaptation) tuplets for all server layer potential interfaces."""
        interfaces = []
        for adaptation in self.serveradaptations.values():
            if adaptation.potentialserver:
                interfaces.append((adaptation.potentialserver, adaptation.function))
        return interfaces
    def isClientMultiplexingInterface(self):
        """Return True if the interface is (potentially) one of multiple channels in a multiplexing adaptation.
        This is determined by the adaptation functions."""
        adaptation = self.getServerAdaptationFunction()
        if adaptation == None:
            return False   # no adaptatation underneath
        else:
            clientcount = adaptation.getClientCount()  # max. number of clients; None means unlimited
            return (clientcount != 1)
    def getServerStackInterfaces(self, curlist=None):
        """Recursively fetch all server layer interfaces, building a full external adaptation stack"""
        if curlist == None:
            curlist = []
        # depth first tree search with duplicate elimination
        for (interface,adaptation) in self.getAllServerTuples():
            if interface in curlist:
                continue
            interface.getServerStackInterfaces(curlist)
            curlist.append(interface)
        return curlist
    

    def getLogicalInterfaces(self):
        """
        returns a plain list of all logical interfaces associated with the current interface. 
        Duplicates are eliminated. The default order is starting at the physical layer, going to 
        the logical channels. Inverse multiplexing channels come after multiplexing channels.
        """
        logicalinterfaces = []
        for interface in self.getServerStackInterfaces():
            if interface not in logicalinterfaces:
                logicalinterfaces.append(interface)
        if self not in logicalinterfaces:
            logicalinterfaces.append(self)
        for interface in self.getClientStackInterfaces():
            if interface not in logicalinterfaces:
                logicalinterfaces.append(interface)
        return logicalinterfaces
    
    def setBroadcastSegment(self, segment):
        assert(self.actual)  # only actual (not potential) interfaces can have connections
        segment.addConnectedInterface(self)      # this sets self.linkedSegment
    def getBroadcastSegment(self):
        return self.linkedSegment
    
    def getLinkedInterfaces(self):
        """Return all linkedTo interface, either described by a linkedTo to an Interface or a 
        linkedTo via a broadcast segment"""
        if self.linkedSegment:
            interfaces = self.linkedInterfaces[:]  # make a copy, as we modify the list
            interfaces.extend(self.linkedSegment.getOtherInterfaces(self))
            return interfaces
        else:
            return self.linkedInterfaces
    
    def getLinkedInterfacesOnly(self):
        """Return all linkedTo interface, excluding those linked via a broadcast segment"""
        return self.linkedInterfaces
    
    def getConnectedInterfacesOnly(self):
        """Return all connectedTo Interfaces, excluding linkedTo"""
        return self.connectedInterfaces
    
    def getConnectedInterfaces(self):
        """Return all connectedTo Interfaces, including linkedTo"""
        interfaces =  self.connectedInterfaces[:]  #make a copy
        interfaces.extend(self.getLinkedInterfaces())
        return interfaces
    
    def addLinkedInterface(self, interface):
        assert(self.actual)  # only actual (not potential) interfaces can have connections
        if self.getLayer() != interface.getLayer():
            raise pynt.ConsistencyException("Can not link interface %s to %s: non matching layers %s and %s." \
                    % (interface.getName(), self.getName(), interface.getLayer(), self.getLayer()))
        if not interface in self.linkedInterfaces:
            if len(self.linkedInterfaces) > 0:
                raise pynt.ConsistencyException(("Can not link interface %s to %s: this interface is already linkedTo %s. " \
                        "If you want to link to multiple hosts, use a BroadcastSegment.") \
                        % (interface.getName(), self.getName(), self.linkedInterfaces[0].getName()))
            if (len(interface.linkedInterfaces) > 0) and (self not in interface.linkedInterfaces):
                raise pynt.ConsistencyException(("Can not link interface %s to %s: that interface is already linkedTo %s. " \
                        "While this is technically possible (unidirectional traffic), we do not recommend it now.") \
                        % (interface.getName(), self.getName(), interface.linkedInterfaces[0].getName()))
            self.linkedInterfaces.append(interface)
    
    def addConnectedInterface(self, interface):
        assert(self.actual)  # only actual (not potential) interfaces can have connections
        # Conneciton between different layers is now only a warning, not an exception.
        # This is because it can occur, especially at domain boundaries.
        if self.getLayer() != interface.getLayer():
            self.logger.warning("Connecting interface %s to %s: non matching layers %s and %s." \
                    % (interface.getName(), self.getName(), interface.getLayer(), self.getLayer()))
        if not interface in self.connectedInterfaces:
            self.connectedInterfaces.append(interface)
    
    def getActualSwitchedInterfaces(self, bidirectional=False):
        """Return all actual switched interfaces, including packet and circuit switched interfaces, and those 
        implicitly set by the switch matrix."""
        if self.switchmatrix:
            return self.switchmatrix.getActualSwitchedInterfaces(self, bidirectional=bidirectional)
        else:
            peerinterfaces = self.getDirectlySwitchedInterfaces()
            if bidirectional:       # filter for reverse cross connects if bidirectional is set
                peerinterfaces = [peerinterface for peerinterface in peerinterfaces if (self in peerinterface.getDirectlySwitchedInterfaces())]
            return peerinterfaces
    
    def getDirectlySwitchedInterfaces(self):
        """Return explicitly configured switched interfaces, including packet and circuit switched interfaces, 
        but excluding implicit switches, as defined in the switch matrix."""
        interfaces = self.switchedInterfaces[:]
        interfaces.extend(self.packetSwtInterfaces)
        interfaces.extend(self.circuitSwtInterfaces)
        return interfaces
    
    def getSwitchSourceInterfaces(self):
        """Return the source interface(s) which is crossed to this interface."""
        return self.switchFromInterfaces[:]  # make a copy
    
    def getPotentialSwitchedInterfaces(self, bidirectional=False, honourlabel=False):
        """Return all possible switched interfaces, by quering the switchmatrix"""
        if self.switchmatrix:
            return self.switchmatrix.getPotentialSwitchedInterfaces(self, bidirectional=bidirectional, honourlabel=honourlabel)
        else:
            return self.getActualSwitchedInterfaces(bidirectional=bidirectional)
    
    def getAvailableSwitchedInterfaces(self, bidirectional=False, breakself=False, allowmerge=False, honourlabel=False):
        """Return all possible switched interfaces, by quering the switchmatrix. 
        The meaning of the parameter toggles are explained with the switch matrix."""
        if self.switchmatrix:
            return self.switchmatrix.getAvailableSwitchedInterfaces(self, bidirectional=bidirectional, breakself=breakself, allowmerge=allowmerge, honourlabel=honourlabel)
        else:
            return self.getActualSwitchedInterfaces(bidirectional=bidirectional)
    
    def setSwitchMatrix(self, switchmatrix):
        if switchmatrix == self.switchmatrix:
            return
        if self.switchmatrix:
            raise pynt.ConsistencyException(("Can not add switch matrix %s to interface %s: the interface already belongs " \
                    "to switch matrix %s.") % (switchmatrix.getName(), self.getName(), self.switchmatrix.getName()))
        self.switchmatrix = switchmatrix
        switchmatrix.addInterface(self)
    
    def getSwitchMatrix(self):
        return self.switchmatrix
    
    def getPacketSwitchedInterfaces(self):
        return self.packetSwtInterfaces
    
    def getCircuitSwitchedInterfaces(self):
        return self.circuitSwtInterfaces
    
    def addSwitchedInterface(self, interface, bidirectional=False):
        if interface in self.switchedInterfaces:
            if bidirectional and self not in interface.switchedInterfaces:
                interface.addSwitchedInterface(self, bidirectional=bidirectional)
            return  # cross connect already explicitly exists
        if not self.actual:
            raise pynt.ConsistencyException("Can not create a switchTo from a potential interface %s" % (self))
        if not interface.actual:
            raise pynt.ConsistencyException("Can not create a switchTo to a potential interface %s" % (interface))
        if bidirectional and (self == interface):
            raise pynt.ConsistencyException("Can not create a a bidirectional loopback from/to %s" % (self))
        if self.getLayer() != interface.getLayer():
            raise pynt.ConsistencyException("Can not switch interface %s to %s: non matching layers %s and %s." \
                    % (self.getName(), interface.getName(), self.getLayer(), interface.getLayer()))
        if len(interface.getSwitchSourceInterfaces()) > 0:
            raise pynt.ConsistencyException("Can not switch interface %s to %s: %s already switches to %s." \
                    % (self.getName(), interface.getName(), interface.getSwitchSourceInterfaces()[0], interface.getName()))
        if self.switchmatrix:
            # check if we should make a switch to (it does not exist implicitly).
            # also raises ConsistencyException is 
            if not self.switchmatrix.shouldMakeSwitchTo(self, interface):
                self.logger.debug("Skip making switchTo from %s to %s: switch already implicitly exists." \
                        % self, interface)
                return
        self.switchedInterfaces.append(interface)
        interface.switchFromInterfaces.append(self)
        try:
            if bidirectional and self not in interface.switchedInterfaces:
                interface.addSwitchedInterface(self, bidirectional=bidirectional)
        except pynt.ConsistencyException:
            self.switchedInterfaces.remove(interface)
            interface.switchFromInterfaces.remove(self)
            raise
    def addPacketSwitchedInterface(self, interface):
        if self.getLayer() != interface.getLayer():
            raise pynt.ConsistencyException("Can not switch interface %s to %s: non matching layers %s and %s." \
                    % (interface.getName(), self.getName(), interface.getLayer(), self.getLayer()))
        if not interface in self.packetSwtInterfaces:
            self.packetSwtInterfaces.append(interface)
    
    def addCircuitSwitchedInterface(self, interface):
        if self.getLayer() != interface.getLayer():
            raise pynt.ConsistencyException("Can not switch interface %s to %s: non matching layers %s and %s." \
                    % (interface.getName(), self.getName(), interface.getLayer(), self.getLayer()))
        if not interface in self.circuitSwtInterfaces:
            self.circuitSwtInterfaces.append(interface)
    
    def getCreateAdaptationInterface(self, klass, identifier="", namespace=None, name="", identifierappend="", nameappend=""):
        """Create a new logical interface instance, with the properties inhereted from this interface, 
        assuming the new interface is adaptation to/from this interfaces. 
        Does not set the adaptation to the current interface yet."""
        # TODO: also specify adaptation function, deduce layer, and assign layer and adaptation as well
        if not identifier:
            identifier  = self.getName() + identifierappend
        if not name:
            name        = self.getName() + nameappend
        if not namespace:
            namespace   = self.getNamespace()
        interface = GetCreateConnectionPoint(identifier=identifier, namespace=namespace, klass=klass)
        # Do not use initfunction anymore; the device or layer may not have been set, even if the peer interface already exists.
        self.setAdaptationInterfaceProperties(interface)
        interface.setName(name)
        return interface
    
    def setAdaptationInterfaceProperties(self, logicalinterface):
        """Copy values of the current interface to the logicalinterface.
        Only copy those values that must be the same if the interfaces are adapted in each other."""
        logicalinterface.setDevice(self.getDevice())
        logicalinterface.setBlade(self.getBlade())
        logicalinterface.setPort(self.getPort())
    
    def getCreateSwitchedInterface(self, identifier, namespace=None):
        """Create a new logical interface instance, with the properties inhereted from this interface, 
        assuming the new interface is switchedTo this interfaces. 
        Does not set the switchedTo property yet."""
        if not namespace:
            namespace   = self.getNamespace()
        klass = type(self)
        interface = GetCreateConnectionPoint(identifier=identifier, namespace=namespace, klass=klass)
        # Do not use initfunction anymore; the device or layer may not have been set, even if the peer interface already exists.
        self.setSwitchedInterfaceProperties(interface)
        return interface
    
    def setSwitchedInterfaceProperties(self, logicalinterface):
        """Copy values of the current interface to the logicalinterface.
        Only copy those values that must be the same if the interfaces are switched to each other."""
        device = self.getDevice()
        peerdevice = logicalinterface.getDevice()
        if device:
            self.logger.debug("Set device of interface %s to %s due to switchTo from %s" \
                    % (logicalinterface.getIdentifier(), device.getIdentifier(), self.getIdentifier()))
            logicalinterface.setDevice(device)
        elif peerdevice:
            self.logger.debug("Set device of interface %s to %s due to switchTo from %s" \
                    % (self.getIdentifier(), peerdevice.getIdentifier(), logicalinterface.getIdentifier()))
            self.setDevice(peerdevice)
        layer = self.getLayer()
        peerlayer = logicalinterface.getLayer()
        if layer:
            self.logger.debug("Set layer of interface %s to %s due to switchTo from %s" \
                    % (logicalinterface.getIdentifier(), layer.getIdentifier(), self.getIdentifier()))
            logicalinterface.setLayer(layer)
        elif peerlayer:
            self.logger.debug("Set layer of interface %s to %s due to switchTo from %s" \
                    % (self.getIdentifier(), peerlayer.getIdentifier(), logicalinterface.getIdentifier()))
            self.setLayer(peerlayer)
        switchmatrix = self.getSwitchMatrix()
        peerswitchmatrix = logicalinterface.getSwitchMatrix()
        if switchmatrix:
            self.logger.debug("Set switch matrix of interface %s to %s due to switchTo from %s" \
                    % (logicalinterface.getIdentifier(), switchmatrix.getIdentifier(), self.getIdentifier()))
            logicalinterface.setSwitchMatrix(switchmatrix)
        elif logicalinterface.getSwitchMatrix():
            self.logger.debug("Set switch matrix of interface %s to %s due to switchTo from %s" \
                    % (self.getIdentifier(), peerswitchmatrix.getIdentifier(), logicalinterface.getIdentifier()))
            self.setSwitchMatrix(peerswitchmatrix)
        # Do not set label; this may not be equal for switch matrices with a swapping capability.
    
    def getCreateConnectedInterface(self, identifier, namespace=None):
        """Create a new logical interface instance, with the properties inhereted from this interface, 
        assuming the new interface is connectedTo this interfaces. 
        Does not set the connectedTo property yet."""
        if not namespace:
            namespace   = self.getNamespace()
        klass = type(self)
        interface = GetCreateConnectionPoint(identifier=identifier, namespace=namespace, klass=klass)
        # check if just fetched interface belongs to this device
        return interface
    


# Mix-Ins (kind of decorators) for Connection Points:
# - SingleLabelCPMixIn      A connection point with an actual label
# - MultiLabelCPMixIn       A connection point with multiple labels
# - SinglePropertyCPMixIn   A connection point with an actual layer properties (e.g. MTU size)
# - MultiPropertyCPMixIn    A connection point with multiple allowed layer properties

# Note that all these mix-in MUST NOT OVERLAP, unless you know what you are doing: 
# The ConfigurableInterface is a subclass of all 4 MixIns, and clashes must be prevented.

class SingleLabelCPMixIn(object):
    """Mix-in for a connection point with a single label. Either for a static, instantiated or configurable interface."""
    layer                   = None  # used to find label type (int, float, ...)
    #hasinternallabel        = None  # None = unknown (use layer and switch matrix to determine), False = no, True = yes
    hasexternallabel        = None  # None = unknown (use adaptation to determine), False = no, True = yes
    #labelvalue              = None  # label, used to identify channels in multiplexing.
    ingresslabel            = None  # label used to signify traffic on an outgoing interface. subproperty of labelvalue.
    egresslabel             = None  # label used to signify traffic received on an interface. subproperty of labelvalue.
    # internal label needs to be replaced by ingress/egress label
    internallabel           = None  # label used to determine switching/swapping possibilities. subproperty of labelvalue.
    def __init__(self):
        pass
    def hasExternalLabel(self):
        # NOTE: same function as MultiLabelCPMixIn.hasExternalLabel(). If you change this function, also change that one.
        if self.hasexternallabel != None:
            return self.hasexternallabel
        adaptation = self.getServerAdaptationFunction()
        if adaptation != None:
            clientcount = adaptation.getClientCount()  # max. number of clients; None means unlimited
            return (clientcount != 1)   # True if there is a multiplexing adaptatation underneath
        elif self.layer:  # no adaptation. Let the layer decide.
            return (self.layer.internallabelprop == None)  # If there is no special internal label, then the label is external
        # The default is True.
        return True
    def setHasExternalLabel(self, boolean):
        self.hasexternallabel = bool(boolean)
    def getLabelTypeAndInterval(self):
        """Use the layer to return the tuplet (type, interval)"""
        if self.layer:
            labelset = self.layer.getLabelSet()
            return (labelset.itemtype, labelset.interval)  # may just the defaul labelset if not defined
        else:
            return (int, 1)
    def getNoLabel(self):
        """Set the labelvalues to a value signifying this layer has no labels, but we can still do calculation with it."""
        # TODO: this is a quick hack. We need another way to signify "the empty label"
        (itemtype, interval) = self.getLabelTypeAndInterval()
        return pynt.rangeset.RangeSet(None, itemtype=itemtype, interval=interval)
    def isAllowedLabel(self, labelvalue):
        if self.layer:
            return self.layer.isAllowedLabel(labelvalue)
        return True # no checking for single label values.
        # return self.isAllowedInternalLabel(labelvalue) and self.isAllowedEgressLabel(labelvalue) and self.isAllowedIngressLabel(labelvalue)
    def isAllowedInternalLabel(self, labelvalue):
        if self.layer:
            return self.layer.isAllowedInternalLabel(labelvalue)
        return True # no checking for single label values.
    def isAllowedEgressLabel(self, labelvalue):
        if self.layer:
            return self.layer.isAllowedEgressLabel(labelvalue)
        return True # no checking for single label values.
    def isAllowedIngressLabel(self, labelvalue):
        if self.layer:
            return self.layer.isAllowedIngressLabel(labelvalue)
        return True # no checking for single label values.
    def setLabel(self, labelvalue):
        if not self.isAllowedLabel(labelvalue):
            raise pynt.ConsistencyException(("Can not set label of configurable interface %s to %s, as this value " \
                    "is not part of the labelset %s") % (self, labelvalue, self.getLabelSet()))
        self.setInternalLabel(labelvalue)
        self.setIngressLabel(labelvalue)
        self.setEgressLabel(labelvalue)
    def setInternalLabel(self, labelvalue):
        assert(not isinstance(labelvalue, pynt.rangeset.RangeSet)), "setInternalLabel only takes primitive labels. Got %s" % labelvalue
        if not self.isAllowedInternalLabel(labelvalue):
            raise pynt.ConsistencyException(("Can not set internal label of configurable interface %s to %s, " \
                    "as this value is not part of the internal labelset %s") % (self, labelvalue, self.getLabelSet()))
        self.internallabel     = labelvalue
    def setIngressLabel(self, labelvalue):
        assert(not isinstance(labelvalue, pynt.rangeset.RangeSet)), "setIngressLabel only takes primitive labels. Got %s" % labelvalue
        if not self.isAllowedIngressLabel(labelvalue):
            raise pynt.ConsistencyException(("Can not set ingress label of configurable interface %s to %s, " \
                    "as this value is not part of the ingress labelset %s") % (self, labelvalue, self.getLabelSet()))
        self.ingresslabel     = labelvalue
    def setEgressLabel(self, labelvalue):
        assert(not isinstance(labelvalue, pynt.rangeset.RangeSet)), "setEgressLabel only takes primitive labels. Got %s" % labelvalue
        if not self.isAllowedEgressLabel(labelvalue):
            raise pynt.ConsistencyException(("Can not set egress label of configurable interface %s to %s, " \
                    "as this value is not part of the egress labelset %s") % (self, labelvalue, self.getLabelSet()))
        self.egresslabel     = labelvalue
    def getLabel(self):
        if self.internallabel != None:
            return self.internallabel
        elif self.egresslabel != None:
            return self.egresslabel
        elif self.ingresslabel != None:
            return self.ingresslabel
        return None
    def getInternalLabel(self):
        return self.internallabel
    def getIngressLabel(self):
        return self.ingresslabel
    def getEgressLabel(self):
        return self.egresslabel
    def getLabelSet(self):
        labelvalue = self.getLabel()
        (itemtype, interval) = self.getLabelTypeAndInterval()
        if labelvalue == None:
            return self.getNoLabel()
        return pynt.rangeset.RangeSet(labelvalue, itemtype=itemtype, interval=interval)
    def getInternalLabelSet(self):
        labelvalue = self.getInternalLabel()
        (itemtype, interval) = self.getLabelTypeAndInterval()
        return pynt.rangeset.RangeSet(labelvalue, itemtype=itemtype, interval=interval)
    def getIngressLabelSet(self):
        labelvalue = self.getIngressLabel()
        (itemtype, interval) = self.getLabelTypeAndInterval()
        return pynt.rangeset.RangeSet(labelvalue, itemtype=itemtype, interval=interval)
    def getEgressLabelSet(self):
        labelvalue = self.getEgressLabel()
        (itemtype, interval) = self.getLabelTypeAndInterval()
        return pynt.rangeset.RangeSet(labelvalue, itemtype=itemtype, interval=interval)
    # TODO: the allow* and *labelsetToStr are really ugly helper functions to deal with all sorts of special cases such as 
    # "no label allowed" and "all labels allowed". Ideally, this ought to be handled in the datatype module, if that is finished.
    def allowAnyInternalLabel(self):
        """Are there no restrictions for the internal label?"""
        if self.layer == None:
            return True     # no layer means no restrictions
        return self.layer.allowAnyInternalLabel()
    def allowNoInternalLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        if self.layer != None:
            return self.layer.allowNoInternalLabel()
        return False    # no layer means no restrictions
    def allowNoneInternalLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        return self.isAllowedInternalLabel(None)
    def allowAnyIngressLabel(self):
        """Are there no restrictions for the internal label?"""
        if self.layer == None:
            return True     # no layer means no restrictions
        return self.layer.allowAnyIngressLabel()
    def allowNoIngressLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        if self.layer != None:
            return self.layer.allowNoIngressLabel()
        return False    # no layer means no restrictions
    def allowNoneIngressLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        return self.isAllowedIngressLabel(None)
    def allowAnyEgressLabel(self):
        """Are there no restrictions for the internal label?"""
        if self.layer == None:
            return True     # no layer means no restrictions
        return self.layer.allowAnyEgressLabel()
    def allowNoEgressLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        if self.layer != None:
            return self.layer.allowNoEgressLabel()
        return False    # no layer means no restrictions
    def allowNoneEgressLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        return self.isAllowedEgressLabel(None)
    def internalLabelSetToStr(self):
        return '['+str(self.internallabel)+']'
    def ingressLabelSetToStr(self):
        return '['+str(self.ingresslabel)+']'
    def egressLabelSetToStr(self):
        return '['+str(self.egresslabel)+']'
    def LabelsToStr(self):
        return "int: %s %s  egr: %s %s  ing: %s %s" % (self.getInternalLabel(), self.internalLabelSetToStr(), 
                self.getEgressLabel(), self.egressLabelSetToStr(), self.getIngressLabel(), self.ingressLabelSetToStr())


class MultiLabelCPMixIn(object):
    """Mix-in for a connection point with multiple labels. Either a list of interfaces, or a potential interface."""
    layer                   = None  # used to find label type (int, float, ...)
    #hasinternallabel        = None  # None = unknown (use layer and switch matrix to determine), False = no, True = yes
    hasexternallabel        = None  # None = unknown (use adaptation to determine), False = no, True = yes
    # internallabels is to be replaced by ingress/egress labels
    internallabels          = None  # None means: no checking. Set to Range(None) to only allow None value.
    ingresslabels           = None  # None means: no checking. Set to Range(None) to only allow None value.
    egresslabels            = None  # None means: no checking. Set to Range(None) to only allow None value.
    def __init__(self):
        pynt.logger.InitLogger()
        self.logger = logging.getLogger("pynt.elements")
        
        # we do not set the labelvalues to an empty RangeSet, simply because we do not 
        # know the type (float, int, ...), since the layer may not be set during instantiation.
    #def hasInternalLabel(self):
    #    if self.hasinternallabel != None:
    #        return self.hasinternallabel
    #def setHasInternalLabel(self, boolean):
    #    self.hasinternallabel = bool(boolean)
    def hasExternalLabel(self):
        # NOTE: same function as SingleLabelCPMixIn.hasExternalLabel(). If you change this function, also change that one.
        if self.hasexternallabel != None:
            return self.hasexternallabel
        adaptation = self.getServerAdaptationFunction()
        if adaptation != None:
            clientcount = adaptation.getClientCount()  # max. number of clients; None means unlimited
            return (clientcount != 1)   # True if there is a multiplexing adaptatation underneath
        elif self.layer:  # no adaptation. Let the layer decide.
            return (self.layer.internallabelprop == None)  # If there is no special internal label, then the label is external
        # The default is True.
        return True
    def setHasExternalLabel(self, boolean):
        self.hasexternallabel = bool(boolean)
    def getLabelTypeAndInterval(self):
        """Use the layer to return the tuplet (type, interval)"""
        # TODO: Use layer
        return (int, 1)
    def getNoLabel(self):
        """Set the labelvalues to a value signifying this layer has no labels, but we can still do calculation with it."""
        # TODO: this is a quick hack. We need another way to signify "the empty label"
        (itemtype, interval) = self.getLabelTypeAndInterval()
        return pynt.rangeset.RangeSet(None, itemtype=itemtype, interval=interval)
    # TODO: the allow* and *labelsetToStr are really ugly helper functions to deal with all sorts of special cases such as 
    # "no label allowed" and "all labels allowed". Ideally, this ought to be handled in the datatype module, if that is finished.
    def allowAnyInternalLabel(self):
        """Are there no restrictions for the internal label?"""
        if (self.internallabels != None):
            return False
        elif self.layer == None:
            return True     # no layer means no restrictions
        return self.layer.allowAnyInternalLabel()
    def allowNoInternalLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        if (self.internallabels != None):
            return self.internallabels.isempty()
        elif self.layer != None:
            return self.layer.allowNoInternalLabel()
        return False    # no layer means no restrictions
    def allowNoneInternalLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        return self.isAllowedInternalLabel(None)
    def allowAnyIngressLabel(self):
        """Are there no restrictions for the internal label?"""
        if (self.ingresslabels != None):
            return False
        elif self.layer == None:
            return True     # no layer means no restrictions
        return self.layer.allowAnyIngressLabel()
    def allowNoIngressLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        if (self.ingresslabels != None):
            return self.ingresslabels.isempty()
        elif self.layer != None:
            return self.layer.allowNoIngressLabel()
        return False    # no layer means no restrictions
    def allowNoneIngressLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        return self.isAllowedIngressLabel(None)
    def allowAnyEgressLabel(self):
        """Are there no restrictions for the internal label?"""
        if (self.egresslabels != None):
            return False
        elif self.layer == None:
            return True     # no layer means no restrictions
        return self.layer.allowAnyEgressLabel()
    def allowNoEgressLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        if (self.egresslabels != None):
            return self.egresslabels.isempty()
        elif self.layer != None:
            return self.layer.allowNoEgressLabel()
        return False    # no layer means no restrictions
    def allowNoneEgressLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        return self.isAllowedEgressLabel(None)
    def internalLabelSetToStr(self):
        if self.allowAnyInternalLabel():
            return '{*}'
        elif self.allowNoInternalLabel():
            return '{None}'
        if self.internallabels:
            labelset = str(self.internallabels)
        else:
            labelset = str(self.layer.getInternalLabelSet())
        if self.allowNoneInternalLabel():
            labelset = labelset[0]+'N,'+labelset[1:]
        return labelset
    def ingressLabelSetToStr(self):
        if self.allowAnyIngressLabel():
            return '{*}'
        elif self.allowNoIngressLabel():
            return '{None}'
        if self.ingresslabels:
            labelset = str(self.ingresslabels)
        else:
            labelset = str(self.layer.getIngressLabelSet())
        if self.allowNoneIngressLabel():
            labelset = labelset[0]+'N,'+labelset[1:]
        return labelset
    def egressLabelSetToStr(self):
        if self.allowAnyEgressLabel():
            return '{*}'
        elif self.allowNoEgressLabel():
            return '{None}'
        if self.egresslabels:
            labelset = str(self.egresslabels)
        else:
            labelset = str(self.layer.getEgressLabelSet())
        if self.allowNoneEgressLabel():
            labelset = labelset[0]+'N,'+labelset[1:]
        return labelset
    def isAllowedLabel(self, labelvalue):
        return self.isAllowedInternalLabel(labelvalue) and self.isAllowedEgressLabel(labelvalue) and self.isAllowedIngressLabel(labelvalue)
        # if self.egresslabels != None:
        #     if labelvalue == None:
        #         return self.egresslabels.isempty()
        #     else:
        #         return labelvalue in self.egresslabels
        # elif self.layer:
        #     return self.layer.isAllowedLabel(labelvalue)
        # return True # no checking for single label values.
    def isAllowedInternalLabel(self, labelvalue):
        if self.internallabels != None:
            if labelvalue == None:
                return self.internallabels.isempty()
            else:
                return labelvalue in self.internallabels
        elif self.layer:
            return self.layer.isAllowedInternalLabel(labelvalue)
        return True # no checking for single label values.
    def isAllowedEgressLabel(self, labelvalue):
        if self.egresslabels != None:
            if labelvalue == None:
                return self.egresslabels.isempty()
            else:
                return labelvalue in self.egresslabels
        elif self.layer:
            return self.layer.isAllowedEgressLabel(labelvalue)
        return True # no checking for single label values.
    def isAllowedIngressLabel(self, labelvalue):
        if self.ingresslabels != None:
            if labelvalue == None:
                return self.ingresslabels.isempty()
            else:
                return labelvalue in self.ingresslabels
        elif self.layer:
            return self.layer.isAllowedIngressLabel(labelvalue)
        return True # no checking for single label values.
    def isValidRestriction(self,iflabelset,labelprop):
        """Check if the desired labelset (for the interface) is a valid restriction, given the 
        labelproperty of the layer. Helper function for setLabelSet functions"""
        # Interface setLabelSet checks if it is allowed by the layer as follows:
        # 
        #         layer    None    {}       {}       {0-50}   {0-50}   {0-99}   {0-99}
        #      labelset:   --      compuls  optional compuls  optional compuls  optional
        # --------------+  None    (any)    (N,any)  0-50     N,0-50   0-99     N,0-99
        # intf labelset:+---------------------------------------------------------------
        # None    (any) |  None    None     None     None     None     None     None
        #               |      (None removes intf restriction, always allowed)
        # {}      None  |  {}      err      {}       err      {}       err      {}
        # {0-50}  0-50  |  err     0-50     0-50     0-50     0-50     0-50     0-50
        # {0-99}  0-99  |  err     0-99     0-99     err      err      0-99     0-99
        if iflabelset == None:
            return True
        elif labelprop == None: # layer has no labelproperty; no label allowed.
            return iflabelset.isempty()
            # Only allow if the labelset also restricts to "nothing allowed" (= only None allowed)
        elif iflabelset.isempty():
            return not labelprop.compulsory
        elif labelprop.range.rangeset.isempty():  # nothing specified; everything is allowed by layer
            return True
        else:
            return labelprop.range.rangeset.issuperset(iflabelset)
    def setLabelSet(self, labelvalues):
        self.setInternalLabelSet(labelvalues)
        self.setIngressLabelSet(labelvalues)
        self.setEgressLabelSet(labelvalues)
    def formatLayerPropertyName(self, labelprop):
        if labelprop == None:
            return "None (nothing allowed)"
        cardinality = (labelprop.compulsory and "compulsory" or "optional")
        return "%s %s %s" % (labelprop.identifier, cardinality, labelprop.range.rangeset)
    def setInternalLabelSet(self, labelvalues):
        if self.layer != None:
            layerprop = self.layer.getInternalLabelProp()
            if not self.isValidRestriction(labelvalues, layerprop):
                raise pynt.ConsistencyException("Can not set internal labelset of interface %s to %s. Layer property %s is stricter" % (self, labelvalues, self.formatLayerPropertyName(layerprop)))
        if labelvalues == None:
            self.internallabels = None
        else:
            self.internallabels = labelvalues.copy()
        if hasattr(self,"internallabel") and not self.isAllowedInternalLabel(self.internallabel):
            # TODO: This should be a check beforehand with ConsistencyException
            self.logger.error("Internal label %s of interface %s is not allowed after setting the labelset to %s" % (self.internallabel, self.getURIdentifier(), self.internallabels))
            raise pynt.ConsistencyException("Internal label %s of interface %s is not allowed after setting the labelset to %s" % (self.internallabel, self.getURIdentifier(), self.internallabels))
    def setIngressLabelSet(self, labelvalues):
        if self.layer != None:
            layerprop = self.layer.getIngressLabelProp()
            if not self.isValidRestriction(labelvalues, layerprop):
                raise pynt.ConsistencyException("Can not set ingress labelset of interface %s to %s. Layer property %s is stricter" % (self, labelvalues, self.formatLayerPropertyName(layerprop)))
        if labelvalues == None:
            self.ingresslabels = None
        else:
            self.ingresslabels = labelvalues.copy()
        if hasattr(self,"ingresslabel") and not self.isAllowedInternalLabel(self.ingresslabel):
            # TODO: This should be a check beforehand with ConsistencyException
            self.logger.error("Ingress label %s of interface %s is not allowed after setting the labelset to %s" % (self.ingresslabel, self.getURIdentifier(), self.ingresslabels))
    def setEgressLabelSet(self, labelvalues):
        if self.layer != None:
            layerprop = self.layer.getEgressLabelProp()
            if not self.isValidRestriction(labelvalues, layerprop):
                raise pynt.ConsistencyException("Can not set egress labelset of interface %s to %s. Layer property %s is stricter" % (self, labelvalues, self.formatLayerPropertyName(layerprop)))
        if labelvalues == None:
            self.egresslabels = None
        else:
            self.egresslabels = labelvalues.copy()
        if hasattr(self,"egresslabel") and not self.isAllowedInternalLabel(self.egresslabel):
            # TODO: This should be a check beforehand with ConsistencyException
            self.logger.error("Egress label %s of interface %s is not allowed after setting the labelset to %s" % (self.egresslabel, self.getURIdentifier(), self.egresslabels))
    def getLabelSet(self):
        if self.internallabels != None:
            return self.internallabels
        elif self.egresslabels != None:
            return self.egresslabels
        elif self.ingresslabels != None:
            return self.ingresslabels
        return self.getNoLabel()
    def getInternalLabelSet(self):
        if self.internallabels != None:
            return self.internallabels
        return self.getNoLabel()
    def getIngressLabelSet(self):
        if self.ingresslabels != None:
            return self.ingresslabels
        return self.getNoLabel()
    def getEgressLabelSet(self):
        if self.egresslabels != None:
            return self.egresslabels
        return self.getNoLabel()
    def setMultiLabelValuesFromCP(self, cp):
        """Copy the values from the given Connection Point to self"""
        self.setInternalLabelSet(getattr(cp, "internallabels", None))
        self.setIngressLabelSet (getattr(cp, "ingresslabels", None))
        self.setEgressLabelSet  (getattr(cp, "egresslabels", None))
    def LabelsToStr(self):
        if isinstance(self, SingleLabelCPMixIn):
            return SingleLabelCPMixIn.LabelsToStr(self)
        else:
            return "int: %s  egr: %s  ing: %s" % (self.internalLabelSetToStr(), 
                    self.egressLabelSetToStr(), self.ingressLabelSetToStr())


class NoLabelCPMixIn(object):
    """Mix-in for a connection point without associated labels. Defines default functions."""
    def __init__(self):
        pass
    def setLabel(self, labelvalue):
        raise NotImplementedError("Can't call setLabel for interfaces without a label, like %s." % self)
    def getLabel(self):
        return None
    def getInternalLabel(self):
        return None
    def getEgressLabel(self):
        return None
    def getIngressLabel(self):
        return None
    def getLabelSet(self):
        return pynt.rangeset.RangeSet(None)
    def getInternalLabelSet(self):
        return pynt.rangeset.RangeSet(None)
    def getEgressLabelSet(self):
        return pynt.rangeset.RangeSet(None)
    def getIngressLabelSet(self):
        return pynt.rangeset.RangeSet(None)
    def hasExternalLabels(self):
        return False



class SinglePropertyCPMixIn(object):
    """A list of values of properties. Specified in the context of a acutal Connection Point.
    The types are now fixed, but should be dynamic, based upon the properties of a specfic layer 
    (see the properties attribute in the Layer object for details)"""
    layer                   = None
    # NOTE: capacity will be moved to properties/potentialproperties
    ingressBandwidth        = None  # float (in Mbyte/s) or None (unknown)
    egressBandwidth         = None  # float (in Mbyte/s) or None (unknown)
    availableCapacity       = None
    # TODO: make this generic; in particular, use the layer properties.
    def __init__(self):
        pass
    def setIngressBandwidth(self,ingressBandwidth): self.ingressBandwidth = float(ingressBandwidth)
    def setEgressBandwidth(self, egressBandwidth):  self.egressBandwidth  = float(egressBandwidth)
    def setAvailableCapacity(self, available):      self.availableCapacity = float(available)
    def getIngressBandwidth(self):                  return self.ingressBandwidth
    def getEgressBandwidth(self):                   return self.egressBandwidth
    def getAvailableCapacity(self):                 return self.availableCapacity


class MultiPropertyCPMixIn(object):
    """A list of allowed values of incompatible properties. Specified in the context of a 
    configurable ConnectionPoint. Only those values that may lead to incompatibilities should 
    be specified. The others are never relevant to specify as the potential capability. 
    The types are now fixed, but should be dynamic, based upon the properties of a specfic layer 
    (see the properties attribute in the Layer object for details)"""
    # TODO: implement as described.
    layer                   = None
    allowedcapacities       = None
    def __init__(self):
        pass
    def setMultiPropertyValuesFromCP(self, cp):
        """Copy the values from the given connection point to self"""
        if cp.configurable:
            self.allowedcapacities = cp.allowedcapacities
        elif cp.actual:
            # raise NotImplementedError ("Can't set allowedcapacities, as the format is yet unclear (range or set)")
            self.allowedcapacities = cp.capacity  # TODO: don't know the type of allowedcapacity
        else:
            NotImplementedError("Can only setMultiPropertyValuesFromCP(cp) for a configurable or configured cp parameter")



# Actual Interface types
# When using Mix-Ins, attributes in the first specified class take precedence.


def InterfaceIdentifier(prefix, blade, port):
    return str(prefix) + str(blade) + '/' + str(port)


class Interface(SingleLabelCPMixIn, SinglePropertyCPMixIn, ConnectionPoint):
    """An interface: a fixed connection point"""
    actual              = True  # signifies that the CP has actual values associated with it.
    removable           = False # signifies that the CP may be marked as configued, and can be removed.
    configurable        = False # signifies that the CP has multiple values, one of them that can be picked.
    potential           = False # signifies that the CP is not "real", but one or more can be instantiated.
    ismultiple          = False # True if this one object (can) represent(s) multiple connection points
    
    def __init__(self, identifier, namespace):
        # WARNING: A RDFObject should always be created using a [Get]CreateRDFObject() function
        # The init function must never create any other RDFObjects, even not indirectly
        ConnectionPoint.__init__(self, identifier=identifier, namespace=namespace)
        SingleLabelCPMixIn.__init__(self)
        SinglePropertyCPMixIn.__init__(self)
    # FIXME: this function should be removed after it is implemented in the RDF devicefetcher
    def setRDFProperty(self, predicate, value):
        if str(predicate) == pynt.xmlns.GetCreateWellKnownNamespace("rdf")["type"]:
            if str(value) == pynt.xmlns.GetCreateWellKnownNamespace("ndl")["ConfiguredInterface"]:
                self.removable = True
            # else:
            #     self.logger.debug("Interface %s is of type %s" % (self.getURIdentifier(), repr(value)))
        elif str(predicate) == pynt.xmlns.GetCreateWellKnownNamespace("ndl")["switchedTo"]:
            (namespace, identifier) = pynt.xmlns.splitURI(value)
            peerinterface = self.getCreateSwitchedInterface(identifier=identifier, namespace=namespace)
            self.addSwitchedInterface(peerinterface)
        elif str(predicate) == pynt.xmlns.GetCreateWellKnownNamespace("ndl")["packetSwitchedTo"]:
            (namespace, identifier) = pynt.xmlns.splitURI(value)
            peerinterface = self.getCreateSwitchedInterface(identifier=identifier, namespace=namespace)
            self.addPacketSwitchedInterface(peerinterface)
        elif str(predicate) == pynt.xmlns.GetCreateWellKnownNamespace("ndl")["circuitSwitchedTo"]:
            (namespace, identifier) = pynt.xmlns.splitURI(value)
            peerinterface = self.getCreateSwitchedInterface(identifier=identifier, namespace=namespace)
            self.addCircuitSwitchedInterface(peerinterface)
        elif str(predicate) == pynt.xmlns.GetCreateWellKnownNamespace("ndl")["capacity"]:
            self.setCapacity(value)
        else:
            #print "-> setting property %s" % predicate
            super(Interface, self).setRDFProperty(predicate, value)
    
    # def getRDFProperty(self, predicate):
    #     """Returns a string, not a rdflib.URIRef!"""
    #     if str(predicate) == pynt.xmlns.GetCreateWellKnownNamespace("rdf")["type"]:
    #         result = [pynt.xmlns.GetCreateWellKnownNamespace("ndl")["Interface"]]
    #         if self.isConfigured():
    #             result.append(pynt.xmlns.GetCreateWellKnownNamespace("ndl")["ConfiguredInterface"])
    #         if self.layer:
    #             result.append(self.layer.getURIdentifier())
    #         return result
    #     # Check if the predicate is in the self.properties list
    #     elif predicate in self.properties.keys():
    #         return self.properties[predicate]
    #     else:
    #         super(Interface, self).getRDFProperty(predicate)

def GetCreateInterface(identifier, namespace, klass=Interface, initfunction=None, **parameters):
    """Create a new interface instance."""
    assert(issubclass(klass, ConnectionPoint))
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=klass, 
            verifyAttributes=False, initfunction=initfunction, **parameters)

class StaticInterface(Interface):
    """Fixed, not configurable interface."""
    actual              = True  # signifies that the CP has actual values associated with it.
    removable           = False  # signifies that the CP may be marked as configued, and can be removed.
    configurable        = False # False, as the list is stored in the Potential Interface. Not in here.
    potential           = False # signifies that the CP is not "real", but one or more can be instantiated.
    ismultiple          = False # True if this one object (can) represent(s) multiple connection points
    pass


# WARNING: the order is important here. SingleLabelCPMixIn must come after MultiLabelCPMixIn
class ConfigurableInterface(MultiLabelCPMixIn, MultiPropertyCPMixIn, Interface):
    actual              = True  # signifies that the CP has actual values associated with it.
    removable           = False # signifies that the CP may be marked as configued, and can be removed.
    configurable        = True  # signifies that the CP has multiple values, one of them that can be picked.
    potential           = False # signifies that the CP is not "real", but one or more can be instantiated.
    ismultiple          = False # True if this one object (can) represent(s) multiple connection points
    def __init__(self, identifier, namespace):
        ConnectionPoint.__init__(self, identifier=identifier, namespace=namespace)
        SingleLabelCPMixIn.__init__(self)
        MultiLabelCPMixIn.__init__(self)
        SinglePropertyCPMixIn.__init__(self)
        MultiPropertyCPMixIn.__init__(self)


class PotentialMuxInterface(MultiLabelCPMixIn, MultiPropertyCPMixIn, ConnectionPoint):
    """A potential interface. A potential interface. This is semantically equivalent with 
    An interface with one of the given labelvalues can be configured by a device."""
    actual              = False # signifies that the CP has actual values associated with it.
    removable           = False # signifies that the CP may be marked as configued, and can be removed.
    configurable        = True  # signifies that the CP has multiple values, one of them that can be picked.
    potential           = True  # signifies that the CP is not "real", but one or more can be instantiated.
    ismultiple          = True  # True if this one object (can) represent(s) multiple connection points
    def __init__(self, identifier, namespace):
        ConnectionPoint.__init__(self, identifier=identifier, namespace=namespace)
        MultiLabelCPMixIn.__init__(self)
        MultiPropertyCPMixIn.__init__(self)


class InstantiatedMuxInterface(Interface):
    """An instantiation of a Potential Interface. Technically, the same as a static Interface: it has a 
    label, but no possible labels (those are listed in the potential Interface).
    Semantically, a MultiplexInterface can be removed, unlike other kinds of Interfaces.
    There should always be an associated Potential Interface with it."""
    actual              = True  # signifies that the CP has actual values associated with it.
    removable           = True  # signifies that the CP may be marked as configued, and can be removed.
    configurable        = False # False, as the list is stored in the Potential Interface. Not in here.
    potential           = False # signifies that the CP is not "real", but one or more can be instantiated.
    ismultiple          = False # True if this one object (can) represent(s) multiple connection points
    pass


# class InterfaceList(MultiLabelCPMixIn, SinglePropertyCPMixIn, ConnectionPoint):
#     """A list of related connection points. It is described as a single Interface, but only with a list of labels.
#     This may be used for inverse multiplexing"""
#     actual              = True  # signifies that the CP has actual values associated with it.
#     removable           = False # signifies that the CP may be marked as configued, and can be removed.
#     configurable        = False # signifies that the CP has multiple values, one of them that can be picked.
#     potential           = False # signifies that the CP is not "real", but one or more can be instantiated.
#     ismultiple          = True  # True if this one object (can) represent(s) multiple connection points
#     interfacecount      = 1
#     # WARNING. We should not (yet) use this class. It is unclear if the labelset represents the 
#     #       *allowed* or *configured* labels.
#     def __init__(self, identifier, namespace):
#         ConnectionPoint.__init__(self, identifier=identifier, namespace=namespace)
#         MultiLabelCPMixIn.__init__(self)
#         SinglePropertyCPMixIn.__init__(self)
#     def getInterfaceCount(self):
#         return self.interfacecount
#     def setInterfaceCount(self, interfacecount):
#         if len(self.getLabelSet() < interfacecount):
#             raise pynt.ConsistencyException("Can not set Interface count of InterfaceList %s to %d. " \
#                     "Only %d free labels are available")
#         self.interfacecount = interfacecount


def GetCreateConnectionPoint(identifier, namespace, klass=Interface, initfunction=None, **parameters):
    """Create a new logical interface instance, with the properties 
    inhereted from this interface. Does not add it to the current interface yet."""
    assert(issubclass(klass, ConnectionPoint))
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=klass, 
            verifyAttributes=False, initfunction=initfunction, **parameters)




class Device(NetworkElement):
    """Abstract device object
    Note: Creating and/or Adding interfaces to a device should be done using the 
    getCreateNativeInterface.    
    """
    blades               = None  # list (set in __init__)
    interfaces           = None  # list (set in __init__)
    logicalinterfaces    = None  # list (set in __init__)
    switchmatrices       = None  # list (set in __init__)
    nativeInterfaceClass = Interface
    domain               = None
    location             = None
    
    def __init__(self, identifier, namespace):
        # WARNING: A RDFObject should always be created using a [Get]CreateRDFObject() function
        # The init function must never create any other RDFObjects, even not indirectly
        NetworkElement.__init__(self, identifier=identifier, namespace=namespace)
        self.blades             = []
        self.interfaces         = []
        self.logicalinterfaces  = []
        self.switchmatrices     = []
        self.namespace.networkschema = True
    
    def setDomain(self, domain):
        self.domain = domain
        domain.addDevice(self)
    def getDomain(self):
        return self.domain
    def unsetDomain(self):
        self.domain.removeDevice(self)
        self.domain = None

    def setLocation(self, location):
        self.location = location
    def getLocation(self):
        return self.location
    def unsetLocation(self):
        self.location = None

    def resetLogicalInterfaceCache(self):
        self.logicalinterfaces = []
    
    def addLogicalInterface(self, interface):
        self.logicalinterfaces.append(interface)
    
    def removeLogicalInterface(self, interface):
        if interface in self.logicalinterfaces:
            self.logicalinterfaces.remove(interface)
    
    def getLogicalInterfaces(self, ordered=False):
        if ordered:
            self.determineLogicalInterfaces()
        return self.logicalinterfaces
    
    def determineLogicalInterfaces(self):
        # returns an sorted list of logical interfaces, by crawling through the physical interfaces
        logicalinterfaces = []
        for interface in self.getNativeInterfaces():
            for logicalinterface in interface.getLogicalInterfaces():
                if logicalinterface not in logicalinterfaces:
                    logicalinterfaces.append(logicalinterface)
        self.logicalinterfaces.sort(key=pynt.xmlns.rdfObjectKey)
        for interface in self.logicalinterfaces:
            if interface not in logicalinterfaces:
                logicalinterfaces.append(interface)
        self.logicalinterfaces = logicalinterfaces
        return self.logicalinterfaces
    
    def getNativeInterfaces(self):
        self.interfaces.sort(key=pynt.xmlns.rdfObjectKey)
        return self.interfaces
    
    def getBlades(self):
        return self.blades
    
    def getCreateNativeInterface(self, identifier, namespace=None, klass=None):
        """
        Return an interface with the given identifier, possible a new object. 
        Note that we return a pointer, so that any changes made to the returned 
        interface object are reflected in the original interface list as well. 
        This is what we want.
        """
        if namespace == None:
            namespace = self.getNamespace()
        if klass == None:
            klass = self.nativeInterfaceClass
        interface = GetCreateConnectionPoint(identifier=identifier, namespace=namespace, klass=klass, 
                initfunction=self.setNewNativeInterfaceProperties)
        return interface
    
    def setNewNativeInterfaceProperties(self, interface):
        """Set pre-set values of the new Interface, before releasing the thread lock.
        Define all values that must be defined in a valid object"""
        interface.setDevice(self)
        # interface.removable = False
        if interface not in self.interfaces:
            self.interfaces.append(interface)
        if interface not in self.logicalinterfaces:
            self.logicalinterfaces.append(interface)
    
    def getCreateBlade(self, bladeno, namespace=None):
        """
        Return an interface with the given blade id, possible a new object. 
        Note that we return a pointer, so that any changes made to the returned 
        interface object are reflected in the original interface list as well. 
        This is what we want.
        """
        bladeno = int(bladeno)
        # check for existing interfaces in this Device
        identifier = BladeIdentifier(bladeno)
        if namespace == None:
            namespace=self.getNamespace()
        blade = pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=Blade, 
                initfunction=self.setNewBladeProperties, bladeno=bladeno)
        # TODO: check if just fetched blade belongs to this device
        return blade
    
    def setNewBladeProperties(self, blade, bladeno):
        """Set pre-set values of the new Blade, before releasing the thread lock.
        Define all values that must be defined in a valid object"""
        self.blades.append(blade)
    
    def getSwitchMatrices(self):        return self.switchmatrices
    
    def addSwitchMatrix(self, switchmatrix):
        if switchmatrix.getDevice() not in [None, self]:
            raise pynt.ConsistencyException("Can not add SwitchMatrix %s to Device %s: it is already in Device %s" \
                    % (switchmatrix.getName(), self.getName(), switchmatrix.getDevice().getName()))
        if switchmatrix not in self.switchmatrices:
            self.switchmatrices.append(switchmatrix)
        if switchmatrix.getDevice() != self:
            switchmatrix.setDevice(self)


def GetCreateDevice(identifier, namespace, klass=Device, initfunction=None, **parameters):
    """Create a new device instance, with the properties inhereted from this interface."""
    assert(issubclass(klass, Device))
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=klass, 
            verifyAttributes=False, initfunction=initfunction, **parameters)


def BladeIdentifier(number):
    return "blade"+str(number)


class Blade(NetworkElement):
    "Blade entry"
    bladeno             = 0     # integer
    vendortype          = ""    # string
    swversion           = ""    # string
    adminstatus         = None  # string "up" or "down" or None (unknown)
    portcount           = 0     # number of interfaces on the blade
    
    def __init__(self, identifier, namespace, bladeno):
        # WARNING: A RDFObject should always be created using a [Get]CreateRDFObject() function
        # The init function must never create any other RDFObjects, even not indirectly
        NetworkElement.__init__(self, identifier=identifier, namespace=namespace)
        self.setNumber(bladeno)
        self.namespace.networkschema = True
    
    def setNumber(self,bladeno):
        self.bladeno        = int(bladeno)
        self.setIdentifier("blade"+str(bladeno))
    def setVendorType(self,vendortype):             self.vendortype     = str(vendortype)
    def setSWVersion(self,swversion):               self.swversion      = str(swversion)
    def setAdminStatus(self,adminstatus):           self.adminstatus    = str(adminstatus)
    def setPortCount(self,portcount):               self.portcount      = int(portcount)
    
    def getNumber(self):                            return self.bladeno
    def getName(self):
        if self.name == "":
            return ("blade %d" % self.getNumber())
        else:
            return self.name
    
    def getVendorType(self):                        return self.vendortype
    def getSWVersion(self):                         return self.swversion
    def getAdminStatus(self):                       return self.adminstatus
    def getPortCount(self):                         return self.portcount



class Adaptation(object):
    """An actual adaptation"""
    function = None     # pointer to the adaptation function
    clients  = None     # list of client interfaces (static, configurable and instantiatedmux interface)
    servers  = None     # list of server interfaces (static, configurable and instantiatedmux interface)
    potentialclient = None  # potential client interface (max 1)
    potentialserver = None  # potential server interface (max 1)
    def __init__(self, adaptationfunction, clientinterface=None, serverinterface=None):
        self.function = adaptationfunction
        self.clients = []
        self.servers = []
        if clientinterface:
            self.addClientInterface(clientinterface)
        if serverinterface:
            self.addServerInterface(serverinterface)
    def addClientInterface(self, interface):
        """Add a client interface (either potential of actual) to an adaptation, provided that 
        the layers match, client count is not exceeded and no duplicate labels are used. Does not 
        add a pointer in the interface to the adaptation."""
        if interface in self.clients:
            return
        assert(isinstance(interface, ConnectionPoint))
        if interface.getLayer() == None:
            raise pynt.ConsistencyException(("Can not add %s as client interface to adaptation %s: " \
                    "interface has no layer defined.") % (interface.getName(), self))
        if self.getDevice() and (interface.getDevice() != self.getDevice()):
            raise pynt.ConsistencyException(("Can not add %s as server interface to adaptation %s: Interface is in " \
                    "device %s, while adaptation is in device %s.") % (interface.getName(), self, interface.getDevice(), 
                    self.getDevice()))
        if self.function.getClientLayer() != interface.getLayer():
            raise pynt.ConsistencyException("Interface %s has layer %s but the client layer of adaptation %s is %s." \
                    % (interface.getName(), interface.getLayer().getName(), self.function.getName(), 
                    self.function.getClientLayer().getName()))
        if interface.isPotential():
            if self.potentialclient not in [None, interface]:
                raise pynt.ConsistencyException(("Adaptation %s already has potential client Interface %s. " \
                        "Ignoring new interface %s.") % (self, self.potentialclient.getIdentifier(), interface.getIdentifier()))
            #if self.function.clientcount and (self.function.clientcount == 1):
            #    raise pynt.ConsistencyException(("Can not add potential client interface %s to adaptation %s: " \
            #            "%s is not a multiplexing adaptation") % (interface.getName(), self, self.function.getName()))
            #if self.isInverseMultiplex():
            #    raise pynt.ConsistencyException(("Can not add potential client interface %s to adaptation %s: " \
            #            "this is already an inverse multiplexing adaptation") \
            #            % (interface.getName(), self))
            self.potentialclient = interface
        elif interface.actual:
            # interface is an actual interface, not a potential interface.
            if self.function.clientcount and (len(self.clients)+1 > self.function.clientcount):
                raise pynt.ConsistencyException(("Can not add %s as client interface to adaptation %s: " \
                        "exceeds client multiplexing count of %d") % (interface.getName(), self, self.function.clientcount))
            if self.isInverseMultiplex() and (len(self.clients) > 0):
                raise pynt.ConsistencyException(("Can not add client interface %s to adaptation %s: " \
                        "this is already an inverse multiplexing adaptation") % (interface.getName(), self))
            label = interface.getLabel()
            if label:
                for client in self.clients:
                    if label == client.getLabel():
                        raise pynt.ConsistencyException(("Can not add %s as client interface to adaptation %s, " \
                                "since label %s is already in use by interface %s.") \
                                % (interface.getName(), self, label, client.getName()))
            self.clients.append(interface)
        else:
            raise pynt.ConsistencyException(("Can not add %s as client interface to adaptation %s: " \
                    "The interface is neither actual or potential") % (interface.getName(), self))
    def removeClientInterface(self, interface):
        """Remove a client interface (either potential of actual) from this adaptation. 
        Warning: does not remove the pointer from the interface to the adaptation."""
        if interface == self.potentialclient:
            self.potentialclient = None
        if interface in self.clients:
            self.clients.remove(interface)
    
    def addServerInterface(self, interface):
        """Add a server layer interface (either potential of actual) to an adaptation, provided 
        that the layers match, server count is not exceeded and no duplicate labels are used."""
        if interface in self.servers:
            return
        assert(isinstance(interface, ConnectionPoint))
        if interface.getLayer() == None:
            raise pynt.ConsistencyException(("Can not add %s as server interface to adaptation %s: " \
                    "interface has no layer defined.") % (interface.getName(), self))
        if self.getDevice() and (interface.getDevice() != self.getDevice()):
            raise pynt.ConsistencyException(("Can not add %s as server interface to adaptation %s: Interface is in device %s, " \
                    "while adaptation is in device %s.") % (interface.getName(), self, interface.getDevice(), self.getDevice()))
        if self.function.getServerLayer() != interface.getLayer():
            raise pynt.ConsistencyException("Interface %s has layer %s but the server layer of adaptation %s is %s." \
                    % (interface.getName(), interface.getLayer().getName(), self.function.getName(), \
                    self.function.getServerLayer().getName()))
        if interface.isPotential():
            # raise NotImplementedError(("Can not add server layer interface %s to adaptation %s. " \
            #         "Potential server layer interfaces have been disabled to reduce the pain levels of our programmers. " \
            #         "While the adaptation code works fine, the consequences for path finding are not understood. " \
            #         "Please describe it as a (list of) ConfigurableInterface(s).") % (interface.getName(), self))
            if self.potentialserver not in [None, interface]:
                raise pynt.ConsistencyException("Adaptation %s already has potential server Interface %s. " \
                        "Ignoring new interface %s." % (self, self.potentialserver.getName(), interface.getName()))
            # potential server interface is only allowed for either:
            # - inverse multiplexing (this represents multiple configurable interfaces)
            # - 1:1 adaptation of potential interface over potentialinterface
            # if self.function.servercount == 1:
            #     raise pynt.ConsistencyException("Can not add potential server interface %s to adaptation %s: " \
            #             "%s is not an inverse multiplexing adaptation" % (interface.getName(), self, self.function.getName()))
            if self.isMultiplex():
                raise pynt.ConsistencyException("Can not add potential server interface %s to adaptation %s: " \
                        "this is already a multiplexing adaptation" % (interface.getName(), self))
            self.potentialserver = interface
        elif interface.actual:
            # interface is an actual interface, not a potential interface.
            if self.function.servercount and (len(self.servers)+1 > self.function.servercount):
                raise pynt.ConsistencyException("Can not add %s as server interface to adaptation %s: " \
                        "exceeds server multiplexing count of %d" % (interface.getName(), self, self.function.servercount))
            if self.isMultiplex() and (len(self.servers) > 0):
                raise pynt.ConsistencyException("Can not add server interface %s to adaptation %s: " \
                        "this is already a multiplexing adaptation" % (interface.getName(), self))
            label = interface.getLabel()
            if label:
                for server in self.servers:
                    if label == server.getLabel():
                        raise pynt.ConsistencyException("Can not add %s as server interface to adaptation %s, " \
                                "since label %s is already in use by interface %s." \
                                % (interface.getName(), self, label, server.getName()))
            self.servers.append(interface)
        else:
            raise pynt.ConsistencyException("Can not add %s as server interface to adaptation %s: The interface " \
                    "is neither actual or potential" % (interface.getName(), self.function.getName()))
    def removeServerInterface(self, interface):
        """Remove a server interface (either potential of actual) from this adaptation."""
        if interface == self.potentialserver:
            self.potentialserver = None
        if interface in self.servers:
            self.servers.remove(interface)
    
    def getClientInterfaces(self):
        """Return actual client interfaces"""
        return self.clients
    def getAllClientInterfaces(self):
        """Return all client interfaces: actual and potential"""
        interfaces = self.clients[:]
        if self.potentialclient:
            interfaces.append(self.potentialclient)
        return interfaces
    def isMultiplex(self):
        if self.function.clientcount != None:
            return self.function.clientcount > 1
        else:
            return (self.potentialclient != None) or (len(self.clients) > 1)
    def isInverseMultiplex(self):
        # This is not considered inverse multiplexing for a potential interfaces over another potential interface
        if self.function.servercount != None:
            return self.function.servercount > 1
        else:
            return (self.potentialserver != None) or (len(self.servers) > 1)
    def actualClientInterfaceCount(self):
        return len(self.clients)
    def allClientInterfaceCount(self):
        if self.potentialclient:
            return 1+len(self.clients)
        else:
            return len(self.clients)
    def hasActualClients(self):
        return len(self.clients) > 0
    def getPotentialClientInterface(self):
        return self.potentialclient
    def hasPotentialClient(self):
        return self.potentialclient != None
    def getAvailableClientLabels(self):
        if not self.hasPotentialClient():
            raise pynt.ConsistencyException("No potential client interface defined to adaptation %s." % (self))
        availablelabels = self.potentialclient.getLabelSet().copy()
        for client in self.clients:
            clientlabel = client.getLabel()
            availablelabels.discard(clientlabel)
        return availablelabels
    def getAvailableClientCount(self):
        if not self.hasPotentialClient():
            return 0
        availablelabels = self.potentialclient.getLabelSet().copy()
        for client in self.clients:
            clientlabel = client.getLabel()
            availablelabels.discard(clientlabel)
        return len(availablelabels)
    
    def getServerInterfaces(self):
        """Return actual server interfaces"""
        return self.servers
    def getAllServerInterfaces(self):
        """Return all server interfaces: actual and potential"""
        interfaces = self.servers[:]
        if self.potentialserver:
            interfaces.append(self.potentialserver)
        return interfaces
    def actualServersInterfaceCount(self):
        return len(self.servers)
    def allServersInterfaceCount(self):
        if self.potentialserver:
            return 1+len(self.servers)
        else:
            return len(self.servers)
    def hasActualServers(self):
        return len(self.servers) > 0
    def getPotentialServerInterface(self):
        return self.potentialserver
    def hasPotentialServer(self):
        return self.potentialserver != None
    def getAvailableServerLabels(self):
        if not self.hasPotentialServer():
            raise pynt.ConsistencyException("No potential server interface defined to adaptation %s." % (self))
        availablelabels = self.potentialserver.getLabels().copy()
        for server in self.servers:
            serverlabel = server.getLabel()
            availablelabels.discard(serverlabel)
        return availablelabels
    def getAvailableServerCount(self):
        if not self.hasPotentialServer():
            return 0
        availablelabels = self.potentialserver.getLabels().copy()
        for server in self.servers:
            serverlabel = server.getLabel()
            availablelabels.discard(serverlabel)
        return len(availablelabels)
    
    def getDevice(self):
        for intf in self.clients:
            if intf.getDevice():
                return intf.getDevice()
        for intf in self.servers:
            if intf.getDevice():
                return intf.getDevice()
        if self.potentialclient and self.potentialclient.getDevice():
            return self.potentialclient.getDevice()
        if self.potentialserver and self.potentialserver.getDevice():
            return self.potentialserver.getDevice()
    def __str__(self):
        return "<Adaptation %s client=%s server=%s>" % (self.function.getName(), self.getAllClientInterfaces(), 
                self.getAllServerInterfaces())
    def __repr__(self):
        return self.__str__()



def CrossConnect(object):
    """Cross connect object, represented by one switchedTo predicates in RDF.
    Multiplexing crossconnect need multiple CrossConnect objects.
    A Cross connect is by itself not a RDF class; this object is used as a placeholder 
    to return (and store) available cross connects and is (will be) used by path finding
    algorithms, and possibly by path objects."""
    source      = None  # The source interface
    destination = None  # The destination interface. For multicast, use multiple CrossConnect instances.
    sourceLabels = None # a Labelset with the allowed labels for the source interface, for this particular cross connect
                        # (must be a subset of the allowed labelset for the source interfaces).
    destinationLabel = None # a single label for the source interface
                        # A None value means that the interfaces has the "None" label.
    sourceLabel = None  # a Labelset with the allowed labels for the source interface, for this particular cross connect
                        # (must be a subset of the allowed labelset for the source interfaces)
    destinationLabel = None # a single label for the destination interface
    pass


# TODO: Distinguish between "Only None Label allowed" and "All labels allowed" (e.g. if label is freeform string, like FiberLayer)


class SwitchMatrix(NetworkElement):
    """Switch matrix of a device. The switch matrix is the dynamic part of a device: the existance 
    of a switch matrix signifies that all interfaces part of it can make cross connects between 
    each other. A switch matrix can switch at one specific layer. Cross connects are also referred 
    to as switches, after switchedTo, the name in NDL to describe cross connects.
    
    A switch matrix has the following properties:
    - switching capability: two interfaces with the same label can be crossed. (default True)
    - swapping capability:  two interfaces with a different label can be crossed. (default False)
    - unicast:   an interface can be crossed to another interface and broken, provided that the 
      labels match, and no other cross connect exist for the source or destination. (default True)
    - multicast: an interface can be crossed to another interface, even if other cross connects 
      with the same source exist. (default False)
    - broadcast: if and only if the labels of two interface matched, they are crossed. 
      Mutual incompatible with unicast. (default False)
    
    The labels as defined above are the internal labels of interfaces. These can be different from 
    the external (egress and ingress) labels, even though in practice the same channel identifier is 
    used. Note that an empty or undefined labelset is considered to be a labelset with one element: 
    the label "None".
     
    Given the switching capabilities of a switch matrix, and the connected interfaces, you can 
    enquire about the following cross connects:
    Actual:         Currently configured cross connects.
    Potential:      Cross connect that can be made by allowing any other cross connect to be broken. 
                    Honours only label sets, not labels and not cross connects.
    Available:      Cross connect that can be made without affecting any existing traffic (cross 
                    connects). Honours label sets, cross connects, but only labels if they are part 
                    of existing cross connects.
    
    By default all checks check for the unidirectional cross connect from source to destination.
    If the bidirectional modifier is given, it checks for the reverse connection as well. 
    In particular, this makes a change for switch matrices with multicast capability.
    
    The "Available" set can be further modified by the modifiers:
    - bidirectional: Makes sure the reverese cross connect is also in place or is (potential) 
                    available. [Actual, Potential, Available]
    - break self:   Do not honour cross connects originating from source and (if bidirectional) 
                    destined to the source interface. All other cross connects remain in place 
                    (including multicast and broadcast cross connects that were part of the same 
                    group). [Available]
    - allow merge:  Allows cross connects that create new data mergers (currently only supported for 
                    broadcast switch matrices with >2 interfaces with the same label.) A merge 
                    may affect the available bandwidth of existing connections. [Available]
    - honour label: Does honour the current label of all interfaces, not just those part of cross 
                    connects. [potential, available]
    
    The above applies to all regular Interfaces (also called "actual" interface, though that has 
    nothing to to with actual cross connects), such as Static Interfaces, Configurable Interfaces 
    and Instantiated Interfaces.
    Potential Interfaces are treated special: they can not have actual cross connection. They are 
    immune to the honourlabel setting in Available cross connects. In this respect, they are threated 
    as multiple interfaces, each with a fixed label equal to the elements in the labelset.
    
    Beside asking for potential and available cross connects, given a to-be-created cross connect, you can enquire 
    about the label that can be used, for both the source and destination interface. This is a subset of the 
    labelset of the respective interfaces.
    """
    layer                   = None  # Layer object or None
    device                  = None  # Device object or None
    hasswitchingcapability  = False
    hasswappingcapability   = False
    hasunicast              = True
    hasmulticast            = False
    hasbroadcast            = False
    canmerge                = False # if True, multiple cross connects can have the same destination
    # TODO: integrate self.canmerge and allowmerge
    lookuptable             = None
    interfaces              = None  # a list
    def __init__(self, identifier, namespace):
        NetworkElement.__init__(self, identifier, namespace)
        self.interfaces = []
        self.namespace.networkschema = True
    
    def setLayer(self, layer):
        assert(isinstance(layer, pynt.layers.Layer))
        self.layer = layer
    def setDevice(self, device):
        if self.device not in [device, None]:
            raise pynt.ConsistencyException("SwitchMatrix %s is part of Device %s. Can not add it to Device %s" \
                    % (self.getName(), self.device.getName(), device.getName()))
        assert(isinstance(device, Device))
        self.device = device
        if self not in device.getSwitchMatrices():
            device.addSwitchMatrix(self)
    
    def setSwitchingCapability(self, switchingcapability):  self.hasswitchingcapability = bool(switchingcapability)
    def setSwappingCapability(self, swappingcapability):    self.hasswappingcapability  = bool(swappingcapability)
    def setUnicast(self, unicast=True):
        self.hasunicast = bool(unicast)
        if self.hasunicast and self.hasbroadcast:
            self.logger.warning("Setting broadcast of SwitchMatrix %s to False, as unicast is set to True" % self.getName())
            self.hasbroadcast = False
        if not self.hasunicast and self.hasmulticast:
            self.logger.warning("Setting multicast of SwitchMatrix %s to False, as unicast is set to False" % self.getName())
            self.hasmulticast = False
    def setMulticast(self, multicast=True):
        self.hasmulticast = bool(multicast)
        if self.hasmulticast and not self.hasunicast:
            self.logger.warning("Setting broadcast of SwitchMatrix %s to False, as unicast is set to True" % self.getName())
            self.hasunicast = True
    def setBroadcast(self, broadcast=True):
        self.hasbroadcast = bool(broadcast)
        if self.hasbroadcast and (self.hasunicast or self.hasmulticast):
            self.logger.warning("Setting unicast of SwitchMatrix %s to False, as broadcast is set to True" % self.getName())
            self.hasunicast = False
            self.hasmulticast = False
    def getLayer(self):                                     return self.layer
    def getDevice(self):                                    return self.device
    def getSwitchingCapability(self):                       return self.hasswitchingcapability
    def getSwappingCapability(self):                        return self.hasswappingcapability
    def canUnicast(self):
        return self.hasunicast
    def canMulticast(self):
        return self.hasmulticast
    def canBroadcast(self):
        return self.hasbroadcast
    def addInterface(self, interface):
        if interface in self.interfaces:
            return
        assert(isinstance(interface, ConnectionPoint))
        if interface.getLayer() != self.getLayer():
            if interface.getLayer() == None:
                raise pynt.ConsistencyException("Can not add unlayered interface %s to %s switch matrix %s." \
                        % (interface.getName(), self.getName(), self.getName()))
            elif self.getLayer() == None:
                raise pynt.ConsistencyException("Can not add %s interface %s to unlayered switch matrix %s." \
                        % (interface.getName(), interface.getDevice().getName(), self.getName()))
            else:
                raise pynt.ConsistencyException("Can not add %s interface %s to %s switch matrix %s." \
                        % (interface.getLayer().getName(), interface.getName(), self.getLayer().getName(), self.getName()))
        if interface.getDevice() != self.getDevice():
            if interface.getDevice() == None:
                raise pynt.ConsistencyException("Interface %s has no Device set, so it can not be added to switch matrix %s " \
                        "in Device %s." % (interface.getName(), self.getName(), self.getDevice().getName()))
            elif self.getDevice() == None:
                raise pynt.ConsistencyException("Can not add interface %s in Device %s to switch matrix %s,  " \
                        "because the switch matrix has no device set." \
                        % (interface.getName(), interface.getDevice().getName(), self.getName()))
            else:
                raise pynt.ConsistencyException("Can not add interface %s in Device %s to switch matrix %s " \
                        "in Device %s." % (interface.getName(), interface.getDevice().getName(), self.getName(), 
                        self.getDevice().getName()))
        self.interfaces.append(interface)
        interface.setSwitchMatrix(self)
    def getInterfaces(self):
        return self.interfaces
    def getOtherInterfaces(self, interface):
        interfaces = self.interfaces[:]
        if interface in interfaces:
            interfaces.remove(interface)
        return interfaces
    def isCompatibleLabel(self, label_or_set1, label_or_set2):
        # a "label matches" if and only if:
        # - if switchingcapability and swappingcapability: true
        # - if switchingcapability labelsets overlap (including configured label, None label): True
        # - elif swappingcapability and labelset are not equal: True
        # - else False
        if self.hasswitchingcapability and self.hasswappingcapability:
            result = True
            #return True  # optimization for common case
        elif self.hasswitchingcapability and label_or_set1 == label_or_set2:
            result = True
            #return True  # optimization for common case. Also takes care if two None labels special case.
        #elif isinstance(label_or_set1, pynt.rangeset.RangeSet) and label_or_set1.isempty():
        #    return True  # special case: empty label can be converted to any other label (TODO: remove special case, and support explicit "empty" labels)
        #elif isinstance(label_or_set2, pynt.rangeset.RangeSet) and label_or_set2.isempty():
        #    return True  # special case: empty label can be converted to any other label (TODO: remove special case, and support explicit "empty" labels)
        else:
            # get the possible labels after switching
            possiblelabels = self.possibleLabelsAfterSwitch(label_or_set1)
            if isinstance(label_or_set2, pynt.rangeset.RangeSet):
                result = possiblelabels.overlaps(label_or_set2)
                #return possiblelabels.overlaps(label_or_set2)
            else:
                result = label_or_set2 in possiblelabels
                #return label_or_set2 in possiblelabels
        #print "%s: isCompatibleLabel(%s, %s) = %s" % (self.getName(), label_or_set1, label_or_set2, result)
        return result
    def getLabelsInUse(self, exceptinterface=None):
        labels = None
        for interface in self.getOtherInterfaces(exceptinterface):
            if labels == None:
                labels = interface.getLabelSet()
            else:
                labels += interface.getLabels()
            
    def possibleLabelsAfterSwitch(self, curlabel_or_labelset):
        """Given a set of labels, return which (internal) labels can be used after switching
        Thus the same labels for switching, and all labels for swapping."""
        if self.hasswitchingcapability and self.hasswappingcapability:
            # return all possible labels for this layer.
            return self.layer.getInternalLabelSet()
        elif self.hasswappingcapability:
            # uncommon: swapping capability, without switching capability
            if isinstance(curlabel_or_labelset, pynt.rangeset.RangeSet) and len(curlabel_or_labelset) > 1:
                return self.layer.getInternalLabelSet()  # everything is possible
            else: # curlabel_or_labelset is a label, not a set.
                return self.layer.getInternalLabelSet() - curlabel_or_labelset   #everything except the current label
        elif self.hasswitchingcapability:
            if isinstance(curlabel_or_labelset, pynt.rangeset.RangeSet):
                return curlabel_or_labelset
            else: # curlabel_or_labelset is a label, not a set.
                return pynt.rangeset.RangeSet(curlabel_or_labelset)   #TODO: set itemtype from layer?
        else: # neither switching nor swapping.
            return pynt.rangeset.RangeSet(None)  # nothing available
    
    
    def getActualSwitchedInterfaces(self, interface, bidirectional=False):
        """Given an interface, get a list of interface where the data is configured to switchedto.
        Get data from both self, as well as interface."""
        def isBidirectional(peerinterface):
            """Helper function. filter for reverse cross connects if bidirectional is set"""
            return (peerinterface != interface) and (interface in peerinterface.getDirectlySwitchedInterfaces())
        
        if not interface.actual:
            return []
        if self.canBroadcast():
            # return interfaces with matching label (based on the current label only)
            interfaces = []
            for peerinterface in self.getOtherInterfaces(interface):
                if not peerinterface.actual:
                    continue
                if self.isCompatibleLabel(interface.getInternalLabel(), peerinterface.getInternalLabel()):
                    interfaces.append(peerinterface)
            return interfaces
        else: # unicast and multicast
            # return all explicitly set switchedTo interfaces.
            peerinterfaces = interface.getDirectlySwitchedInterfaces()
            if bidirectional:       # filter for reverse cross connects if bidirectional is set
                peerinterfaces = filter(lambda peerinterface: isBidirectional(peerinterface), peerinterfaces)
            return peerinterfaces
    def getPotentialSwitchedInterfaces(self, interface, bidirectional=False, honourlabel=False):
        """Given an interface, find potential switchTo from the interface to other interfaces, and return the list 
        of remote interfaces. The list also includes interfaces which are currently in use. Does take the labelset 
        into account. If honourlabel is set, uses the current label instead of the available labelset.
        Honourlabel True is similar to getActualSwitchedInterfaces(), except that it does include PotentialInterfaces."""
        interfaces = []
        # return all interfaces with matching labelsets (or label if no labelset is present)
        if honourlabel or not interface.configurable:
            label = interface.getInternalLabel()
        else:
            label = interface.getInternalLabelSet()
        if bidirectional or self.canBroadcast():  # loopbacks are not allowed for bidirectional or broadcast
            peerinterfaces = self.getOtherInterfaces(interface)
        else:
            peerinterfaces = self.getInterfaces()
        for peerinterface in peerinterfaces:
            if honourlabel or not peerinterface.configurable:
                peerlabel = peerinterface.getInternalLabel()
            else:
                peerlabel = peerinterface.getInternalLabelSet()
            if self.isCompatibleLabel(label, peerlabel):
                interfaces.append(peerinterface)
        return interfaces
    def getAvailableSwitchedInterfaces(self, interface, bidirectional=False, breakself=False, allowmerge=False, honourlabel=False):
        """Given an interface, find available switchTo from the interface to other interfaces, and return the list 
        of remote interfaces. The list is filtered for interfaces which are currently in use."""
        # Define two helper functions:
        def connectToOthers(peer):
            """Helper function. Return True if peer has cross connect to other interfaces beside interface"""
            if not bidirectional and breakself and (peer == interface) and not self.hasbroadcast:
                return False    # special case: allow loopbacks if breakself is set
            peers = self.getActualSwitchedInterfaces(peer, bidirectional=False)   # returns a copy, so we can use remove()
            try:
                peers.remove(interface)
            except ValueError:
                pass
            return len(peers) > 0
        def connectFromOthers(peer):
            """Helper function. Return True if peer is the sink of other cross connect then those originating from interface"""
            if bidirectional and not breakself and (peer == interface) and not self.hasbroadcast:
                return True    # special case: don't allow loopbacks if breakself is not set
            peers = peer.getSwitchSourceInterfaces()   # returns a copy, so we can use remove()
            try:
                peers.remove(interface)
            except ValueError:
                pass
            return len(peers) > 0
        def getBroadcastInterfaceLabelOrLabelset(peer):
            # Ideally, we allow the interface to use all available labels. There are 3 expections:
            if not peer.actual:
                # The interface only no specific label, only a list of possible
                peerlabel = peer.getInternalLabelSet()
            elif (not peer.configurable) or honourlabel:
                # The interface only has one label, not multiple
                # Honourlabel is True: we use the current label (if it is defined)
                peerlabel = peer.getInternalLabel()
            elif (peer == interface) and (not (breakself and bidirectional)) and connectToOthers(peer):
                # The label is used by multiple interfaces in a broadcast matrix; changing the label would break connections
                peerlabel = peer.getInternalLabel()
            elif (peer != interface) and connectToOthers(peer):
                # Actually connectFromOthers(), but that is the same connectToOthers() and correctly includes implicitly defined switches
                peerlabel = peer.getInternalLabel()
            else: # can change label
                peerlabel = peer.getInternalLabelSet()
            return peerlabel
        
        # allowmerge = self.canmerge or allowmerge # TODO: merge these two
        if self.canBroadcast(): # For broadcast switch matrices:
            # 
            # return interfaces with matching label (based on the current label if required, or the labeleset otherwise)
            # if this context, it is "required" to use the current label if there is one or more switched to; thus 
            # if there are other interfaces with the same label.
            #print "Case: bidirectional=%s, breakself=%s, allowmerge=%s, honourlabel=%s" % (bidirectional, breakself, allowmerge, honourlabel)
            label = getBroadcastInterfaceLabelOrLabelset(interface)
            interfaces = self.getActualSwitchedInterfaces(interface, bidirectional=bidirectional)
            for peerinterface in self.getPotentialSwitchedInterfaces(interface, bidirectional=bidirectional, honourlabel=honourlabel):
                if peerinterface in interfaces:
                    continue  # peerinterface already (implicitly) switched. So naturally, it is available too.
                peerlabel = getBroadcastInterfaceLabelOrLabelset(peerinterface)
                if not allowmerge and connectToOthers(peerinterface):
                    #print "%s -> %s: %s, %s: %s (no merge)" % (interface, peerinterface, label, peerlabel, False)
                    continue
                elif self.isCompatibleLabel(label, peerlabel):
                    #print "%s -> %s: %s, %s: %s" % (interface, peerinterface, label, peerlabel, True)
                    interfaces.append(peerinterface)
                else:
                    #print "%s -> %s: %s, %s: %s" % (interface, peerinterface, label, peerlabel, False)
                    pass
            return interfaces
        else: # unicast and multicast switch matrices:
            # the available switched interface consists of two parts:
            # - the current configured switchedTo
            # - potential switchedTo to interfaces which are not (yet) a sink
            actualpeers     = interface.getDirectlySwitchedInterfaces()
            actualpeercount = len(actualpeers)
            reversecrosses  = interface.getSwitchSourceInterfaces()
            if bidirectional and not self.canmerge and len(reversecrosses) > 0:  # TODO: merge allowmerge can self.canmerge
                # Exclude cross connect if another cross to me prevents the peer to make a cross connect back to me.
                actualpeers = filter(lambda peer: (peer != interface) and (peer in reversecrosses), actualpeers)
            if bidirectional and not self.hasmulticast:
                # Exclude cross connect lack of multicast prevents the peer to make a cross connect back to me (and it already has another cross)
                actualpeers = filter(lambda peer: not connectToOthers(peer), actualpeers)
            
            if not self.hasmulticast and not breakself and actualpeercount > 0:
                # there is already an existing switched to; can not add others without multicast.
                return actualpeers    
            if bidirectional and not breakself and not self.canmerge and len(reversecrosses) > 0:  # TODO: merge allowmerge can self.canmerge
                # Another cross is pointing to me. Can't bidirectionally cross to others
                reversecrosses = filter(lambda peer: not connectFromOthers(peer), reversecrosses)
                return reversecrosses
            
            # we can also connect to others, beside the current actual cross connects
            peers = self.getPotentialSwitchedInterfaces(interface, bidirectional=bidirectional, honourlabel=honourlabel)
            # we can switch to all interfaces, provided that the peer interface is not the destination 
            # of an existing cross connect
            if bidirectional and not self.hasmulticast:
                # exclude peers which are the source of an existing cross connect
                peers = filter(lambda peer: not connectToOthers(peer), peers)
            if not self.canmerge:  # TODO: merge allowmerge can self.canmerge
                # exclude peers which are the sink of an existing cross connect
                peers = filter(lambda peer: not connectFromOthers(peer), peers)
            # The conversion to a set removes all duplicates. Arguably, we should return a set anyway, not a list.
            return list(set(actualpeers + peers))
    
    # Function to check compatible labels between two interfaces; returns labels before, after, and if the cross connecpossible
    
    def canSwitchTo(self, interface, tointerface, bidirectional=False, breakself=False, honourlabel=False):
        """switch-matrix specific checks if a switchTo can be made from interface to tointerface. 
        Raises a consistency excecption if it is not possible. returns True if it can be made, 
        returns False if it already (implictly or explicitly) exists, and should not be created"""
        if self.unicast:
            return True
        elif self.broadcast:
            return True
        else:
            raise pynt.ConsistencyException("Switch Matrix %s can neither unicast nor broadcast" % self)
    
    def shouldMakeSwitchTo(self, interface, tointerface):
        """switch-matrix specific checks if a switchTo can be made from interface to tointerface. 
        Raises a consistency excecption if it is not possible. returns True if it can be made, 
        returns False if it already (implictly or explicitly) exists, and should not be created"""
        # Note: generic checks like equal layer, and check if interfaces are "actual" are already made 
        # in Interface.addSwitchedInterface(). These are are only switch-matrix specific checks.
        if interface not in self.interfaces:
            raise pynt.ConsistencyException("Can not switch interface %s to %s, %s is not part of " \
                    "switch matrix %s." % (interface.getName(), tointerface.getName(), interface.getName(), self.getName()))
        if tointerface not in self.interfaces:
            raise pynt.ConsistencyException("Can not switch interface %s to %s, %s is not part of " \
                    "switch matrix %s." % (interface.getName(), tointerface.getName(), tointerface.getName(), self.getName()))
        if interface.getLayer() != self.getLayer():
            raise pynt.ConsistencyException("Can not switch interface %s to %s: layer %s does not match layer %s" \
                    "of switch matrix %s" % (interface.getName(), tointerface.getName(), interface.getLayer(), self.getLayer(), \
                    self.getName()))
        peerinterfaces = self.getActualSwitchedInterfaces(interface, bidirectional=False)
        if tointerface in peerinterfaces:
            return False
        peerinterfaces = self.getAvailableSwitchedInterfaces(interface, bidirectional=False) # not too strict here
        if tointerface not in peerinterfaces:
            raise pynt.ConsistencyException("Can not switch interface %s to %s. Current capability and configuration " \
                    "of switch matrix %s only allow cross connects to %s" % (interface.getName(), tointerface.getName(), \
                    self.getName(), ",".join([intf.getName() for intf in peerinterfaces])))
        return True


def GetCreateSwitchMatrix(identifier, namespace, klass=SwitchMatrix):
    """create a new adaptation with given parameters.
    If an adaptation with the same name exist, check if the properties are the 
    same. If not, raise an exception"""
    assert(issubclass(klass, SwitchMatrix))
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier,namespace=namespace, klass=klass)


class BroadcastSegment(NetworkElement):
    """A virtual link to. All interfaces in a BroadcastSegments are said to be linkedTo each other.
    A Link object is a special case of a BroadcastSegement with exactly two linked interfaces."""
    def __init__(self, identifier, namespace):
        NetworkElement.__init__(self, identifier, namespace=namespace)
        self.interfaces = []
        self.layer = None
        self.namespace.networkschema = True
        self.mask = None
    
    def getLayer(self):             return self.layer
    def setLayer(self, layer):      self.layer = layer
    def getMask(self):              return self.mask
    def setMask(self, mask):        self.mask = mask
    def removeConnectedInterface(self, interface):
        if interface in self.interfaces:
            self.interfaces.remove(interface)
        interface.linkedSegment = None
    def addConnectedInterface(self, interface):
        if interface not in self.interfaces:
            self.interfaces.append(interface)
        # If the interface already is in a broadcast segment,
        # it is removed from that segment.
        if interface.linkedSegment not in [None, self]:
            # hmm, I think you should throw an exception here.
            raise pynt.ConsistencyException("The interface %s is already in BroadcastSegment %s. " \
                    "Remove it there first." % (interface.getURIdentifier(), interface.linkedSegment.getURIdentifier()))
        if interface.linkedSegment != self:
            interface.linkedSegment = self
    
    def getConnectedInterfaces(self):
        return self.interfaces
    def getOtherInterfaces(self, ignoreinterface):
        interfaces = []
        for interface in self.interfaces:
            if interface != ignoreinterface:
                interfaces.append(interface)
        return interfaces

def GetCreateBroadcastSegment(identifier, namespace=None, klass=BroadcastSegment):
    """create a new property with given parameters, or return existing one if it already exists."""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=BroadcastSegment)

class Link(BroadcastSegment):
    pass
    # TODO: Write some stuff to limit connectedInterfaces to two.

def GetCreateLink(identifier, namespace=None, klass=BroadcastSegment):
    """create a new property with given parameters, or return existing one if it already exists."""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=BroadcastSegment)


def GetCreateLocation(identifier, namespace=None):
    """create a new property with given parameters, or return existing one if it already exists."""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=Location)

class Location(NetworkElement):
    """A location is used to group devices. Locations can/should also be part of a domain."""

    def __init__(self, identifier, namespace):
        NetworkElement.__init__(self, identifier, namespace=namespace)


def GetCreateAdminDomain(identifier, namespace=None):
    """create a new property with given parameters, or return existing one if it already exists."""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=AdminDomain)

class AdminDomain(NetworkElement):
    """This class is a container for devices in a network domain. Also see the
       NDL domain schema."""

    interfaces = None
    devices = None
    
    def __init__(self, identifier, namespace):
        NetworkElement.__init__(self, identifier, namespace=namespace)
        self.interfaces = []
        self.devices = []
    
    def addDevice(self, device):
        if device not in self.devices:
            self.devices.append(device)
            self.logger.debug("Added device %s to domain %s" % (device.getName(), self.getName()))
        else:
            self.logger.warning("Device %s is already in domain %s" % (device.getName(), self.getName()))
    def removeDevice(self, device):
        if device in self.devices:
            self.devices.remove(device)
            self.logger.debug("Removed device %s from domain %s" % (device.getName(), self.getName()))
        else:
            self.logger.warning("Device %s not found in domain %s when removing device" % (device.getName(), self.getName()))

    def getDevices(self):
        return self.devices

    def addInterface(self, interface):
        logger = logging.getLogger("pynt.elements")
        if interface not in self.interfaces:
            self.interfaces.append(interface)
            self.logger.debug("Added interface %s to domain %s" % (interface.getName(), self.getName()))
        else:
            self.logger.warning("interface %s is already in domain %s" % (interface.getName(), self.getName()))

    def removeInterface(self, interface):
        if interface in self.interfaces:
            self.interfaces.remove(interface)
            self.logger.debug("Removed interface %s from domain %s" % (interface.getName(), self.getName()))
        else:
            self.logger.warning("Interface %s not found in domain %s when removing interface" % (interface.getName(), self.getName()))

    def getInterfaces(self):
        return self.interfaces

