# -*- coding: utf-8 -*-
"""The ethernet module defines a few Ethernet specific network element classes: EthernetDevice, EthernetInterface and Vlan"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns
import pynt.technologies.ip

# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "ethernet"
uri       = 'http://www.science.uva.nl/research/sne/ndl/ethernet#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/ethernet.rdf'
humanurl  = 'http://www.science.uva.nl/research/sne/ndl/?c=20-Technology-Schemas'

def GetNamespace():
    global prefix, uri, schemaurl, humanurl
    return pynt.xmlns.GetCreateNamespace(
        prefix    = prefix,
        uri       = uri,
        schemaurl = schemaurl,
        humanurl  = humanurl,
        layerschema = True,
    )

def GetLayer(shortcut):
    if shortcut == 'mac':
        return pynt.layers.GetCreateLayer('MACNetworkElement',      namespace=GetNamespace(), name="MAC")
        # TODO: add MAC label properties
    elif shortcut == 'ethernet':
        try:
            return pynt.xmlns.GetRDFObject("EthernetNetworkElement", namespace=GetNamespace(), klass=pynt.layers.Layer)
        except pynt.xmlns.UndefinedNamespaceException, e:
            layer = pynt.layers.GetCreateLayer('EthernetNetworkElement', namespace=GetNamespace(), name="Ethernet")
            rangeset = pynt.rangeset.RangeSet("0-4095", itemtype=int, interval=1)
            rangeset = pynt.layers.GetCreateLabelSet("IEEE802-1QLabel", GetNamespace(), rangeset)
            vlanprop = pynt.layers.GetCreateProperty("VLAN", GetNamespace(), rangeset, incompatible=True, compulsory=False)
            tagprop  = pynt.layers.GetCreateProperty("IEEE802-1Q", GetNamespace(), rangeset, incompatible=True, compulsory=False)
            layer.setLabelProperty(tagprop)
            layer.setInternalLabelProperty(vlanprop)
            return layer
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    if name == "MAC-in-Ethernet":
        return pynt.layers.GetCreateAdaptationFunction("MAC-in-Ethernet", namespace=GetNamespace(), clientlayer=pynt.technologies.ethernet.GetLayer('mac'), serverlayer=pynt.technologies.ethernet.GetLayer('ethernet'), clientcount=79228162514264337593543950336, servercount=1, name="MAC in Ethernet")
    elif name == "Tagged-Ethernet":
        return pynt.layers.GetCreateAdaptationFunction("Tagged-Ethernet", namespace=GetNamespace(), clientlayer=pynt.technologies.ethernet.GetLayer('ethernet'), serverlayer=pynt.technologies.ethernet.GetLayer('ethernet'), clientcount=4096, servercount=1, name="Tagged Ethernet")
    elif name == "IP-in-MAC":
        return pynt.layers.GetCreateAdaptationFunction("IP-in-MAC", namespace=GetNamespace(), clientlayer=pynt.technologies.ip.GetLayer('ip'), serverlayer=pynt.technologies.ethernet.GetLayer('mac'), clientcount=1, servercount=1, name="IP in MAC")
    else:
        raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("MACInterface", namespace=GetNamespace(), layer=GetLayer('mac'))

class MACInterface(pynt.elements.Interface):
    """MAC Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('mac')


# pynt.elements.GetCreateInterfaceLayer("EthernetInterface", namespace=GetNamespace(), layer=GetLayer('ethernet'))

class EthernetInterface(pynt.elements.Interface):
    """Ethernet Interface: both for LAN and VLAN (tagged) interfaces"""
    adminstatus         = None  # string "up" or "down" or None (unknown) -> layer egress Property pointing to a boolean
    linkstatus          = None  # string "up" or "down" or None unknown) -> layer ingress Property pointing to a boolean
    mtu                 = None  # integer or None(unknown) -> incompatible layer Property (pointing to a RangeSet)
    MACaddress          = None  # string (lowercase, with : as seperator) or None (unknown) -> layer Property??? (leaky abstraction here; Ethernet sucks...)
    linespeed           = None  # float or None (unknown) = capacity?
    egressbandwidth     = None  # float or None (unknown) -> layer egress Property
    ingressbandwidth    = None  # float or None (unknown) -> layer ingress Property
    tagged_vlanids      = None  # None or list of ints -> client MultiplexInterfaces
    
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('ethernet')
    
    def setRDFProperty(self, predicate, value):
        ns = GetNamespace()
        if str(predicate) == ns["ingressStatus"]:
            self.setLinkStatus(value)
        elif str(predicate) == ns["egressStatus"]:
            self.setAdminStatus(value)
        elif str(predicate) == ns["VLAN"]:
            self.setUntaggedVLANid(value)
        elif str(predicate) == ns["IEEE802-1Q"]:
            self.setLabel(value)
        else:
            super(EthernetInterface, self).setRDFProperty(predicate, value)
    
    def getRDFProperty(self, predicate):
        ns = GetNamespace()
        if str(predicate) == ns["ingressStatus"]:
            return self.getLinkStatus()
        elif str(predicate) == ns["egressStatus"]:
            return self.getAdminStatus()
        elif str(predicate) == ns["VLAN"]:
            return self.getUntaggedVLANid(value)
        elif str(predicate) == ns["IEEE802-1Q"]:
            return self.getEgressLabel(value)
        else:
            super(EthernetInterface, self).getRDFProperty(predicate)
    
    def setAdminStatus(self,adminstatus):
        if adminstatus == None:
            self.adminstatus = None; # unknown
        elif str(adminstatus) in ["up", "down"]:
            self.adminstatus = str(adminstatus)
        else:
            raise AttributeError("Admin status %s not recognized. Valid admin status are 'up' and 'down'" % linkstatus)
    
    def setLinkStatus(self,linkstatus):
        if linkstatus == None:
            self.linkstatus = None; # unknown
        elif str(linkstatus) in ["up", "down"]:
            self.linkstatus = str(linkstatus)
        else:
            raise AttributeError("Link status %s not recognized. Valid link status are 'up' and 'down'" % linkstatus)
    
    def setMTU(self,mtu):
        if mtu == None:
            self.mtu = None;
        else:
            self.mtu = int(mtu)
    
    def setMACaddress(self,MACaddress):
        if MACaddress == None:
            self.MACaddress = None;
        else:
            self.MACaddress = str(MACaddress)
    
    def setLineSpeed(self,linespeed):
        if linespeed == None:
            self.linespeed = None;
        else:
            self.linespeed = float(linespeed)
    
    def setEgressBandwidth(self,egressbandwidth):
        if egressbandwidth == None:
            self.egressbandwidth = None;
        else:
            self.egressbandwidth = float(egressbandwidth)
    
    def setIngressBandwidth(self,ingressbandwidth):
        if ingressbandwidth == None:
            self.ingressbandwidth = None;
        else:
            self.ingressbandwidth = float(ingressbandwidth)
    
    def getAdminStatus(self):                       return self.adminstatus
    def getLinkStatus(self):                        return self.linkstatus
    def getUntaggedVLANid(self):
        if self.tagged_vlanids:
            return None
        else:
            return self.internallabel
    def getTaggedVLANids(self):                     return self.tagged_vlanids
    def getMTU(self):                               return self.mtu
    def getMACaddress(self):                        return self.MACaddress
    def getLineSpeed(self):                         return self.linespeed
    def getEgressBandwidth(self):                   return self.egressbandwidth
    def getIngressBandwidth(self):                  return self.ingressbandwidth
    
    def setLabel(self, labelvalue):
        if self.internallabel and self.internallabel != labelvalue:
            raise pynt.ConsistencyException ("Can not set label value of interface %s to %s, since untagged VLAN is set to %s." % (self.getName(), labelvalue, self.internallabel))
        pynt.elements.Interface.setLabel(self, labelvalue)
    
    def setUntaggedVLANid(self,untagged_vlanid):
        # assert(untagged_vlanid == None or isinstance(untagged_vlanid, (int, long)))
        if self.internallabel and untagged_vlanid and self.internallabel != untagged_vlanid:
            raise pynt.ConsistencyException ("Can not set the untagged VLAN of interface %s to %s, since label value is set to %s." % (self.getName(), untagged_vlanid, self.getInternalLabel()))
        if untagged_vlanid != None:
            untagged_vlanid = int(untagged_vlanid)
        pynt.elements.Interface.setInternalLabel(self, untagged_vlanid)
    
    def addTaggedVLANid(self,vlanid):
        if (None == self.tagged_vlanids):
            self.tagged_vlanids = []
        self.tagged_vlanids.append(vlanid)
    
    def setTaggedVLANids(self,vlanidlist):
        if vlanidlist == None:
            self.tagged_vlanids = None
        elif type(vlanidlist) == types.ListType:
            self.tagged_vlanids = vlanidlist
        else:
            raise TypeError ("Ignoring setTaggedVLANids(list) as the argument is a %s instead of a list" % str(type(vlanidlist)))
            self.tagged_vlanids = []
    
    def setUntaggedInterface(self, vlanid):
        """Assigns the given vlanid to an internal list, returning the current interface.
        Simply overwrite any existing VLANid.
        If a tagged interface already exists, calls createUntaggedClientInterface() which raises an exception."""
        if self.getTaggedVLANids() != None:
            self.createUntaggedClientInterface() # raises an exception
        self.setUntaggedVLANid(vlanid)
        # TODO: check if MAC address is set, and if so, add clientinterface to 
        # the interface. Only do so if it does not exist yet.
        # self.addMACInterface()
        return self
    
    def addTaggedInterface(self, vlanid):
        """Assigns the interface to the given VLAN id, returning the created internal client interface."""
        if self.getUntaggedVLANid() != None:
            self.createUntaggedClientInterface() # raises an exception
        self.addTaggedVLANid(vlanid)
        logicalinterface = self.getTaggedInterface(vlanid)
        if not logicalinterface:
            # Doesn't exist. Create subinterface.
            logicalinterface = self.createTaggedClientInterface(vlanid)
            adaptation = GetCreateWellKnownAdaptationFunction("Tagged-Ethernet")
        self.addClientInterface(logicalinterface, adaptation)
        # TODO: check if MAC address is set, and if so, add clientinterface to 
        # the logicalinterface
        # logicalinterface.addMACInterface()
        return logicalinterface
    
    def createUntaggedClientInterface(self):
        """Create an internal client interface in the current untagged_vlan. Keep the untagged_vlanid value, 
        but removes the current interface from the VLAN, and adds the client interface to the VLAN."""
        # This function SHOULD always raise an error. This is complex function, and should be supported 
        # in the Device object, not here. The reason is simply that the Interface object should not 
        # be aware of the switching (and thus not the VLANs either)
        raise pynt.ConsistencyException ("Interface %s is both tagged (VLANs %s) as well as untagged (VLAN %d). Support for this situation is not yet implemented." % (self.getName(),  str(self.getTaggedVLANids()), self.getUntaggedVLANid()))
    
    def createTaggedClientInterface(self, vlanid):
        """Create a new Ethernet interface instance, with the properties 
        inhereted from this interface. Does not add it to the current interface yet."""
        identifier  = self.getTaggedIdentifier(vlanid)
        name        = self.getTaggedName(vlanid)
        logicalinterface = self.getCreateAdaptationInterface(EthernetInterface, identifier=identifier, name=name)
        logicalinterface.setName(name)
        logicalinterface.setDevice(self.getDevice())
        logicalinterface.removable = True
        logicalinterface.setLabel(int(vlanid))  # for the logical interface, the tagged label acts as the labelvalue
        logicalinterface.setUntaggedVLANid(None)    # Do not assign untagged VLAN id yet, since it may also be a Q-in-Q interface
        logicalinterface.setBlade(self.getBlade())
        logicalinterface.setPort(self.getPort())
        return logicalinterface
    
    # TODO: def removeTaggedInterface function?
    
    # Function is a bit obsolete, but still used a couple of times, so we keep it
    def getTaggedInterface(self,vlanid):
        """Returns the logical interface with the given tag. Returns None if it does not exist"""
        for interface in self.getClientInterfaces():
            if interface.getInternalLabel() == vlanid:
                return interface
        return None
    
    def getTaggedIdentifier(self,vlanid):
        return self.getIdentifier() + ":vlan" + str(vlanid)
    
    def getTaggedName(self,vlanid):
        return self.getName() + " vlan " + str(vlanid)
    
    def addMACInterface(self):
        # TODO: to be written
        # Check if it already exists, or there are inconsistencies
        macaddress = self.getMACaddress()
        macinterface = self.createMACClientInterface(macaddress)
        adaptation = GetCreateWellKnownAdaptationFunction("MACinEthernet-Ethernet")
        self.addClientInterface(macinterface, adaptation)
        return macinterface
    
    def createMACClientInterface(self, MACaddress):
        """return the internal client interface with the given MAC address, appended with the appropriate VLAN identifier."""
        # TODO: to be written
        pass
        return macinterface
    
    def getPacketSwitchedInterfaces(self):
        # TODO: change VLAN to a switch matrix
        vlanid = self.getUntaggedVLANid()
        if vlanid:
            vlan = self.device.getVlan(vlanid)
            return vlan.getOtherPorts(self)
        else:
            return []

# TODO: make  a generic helper funcion, which is NOT a subclass of Interface.

def VlanIdentifier(vlanid):
    return "vlan"+str(vlanid)


# TODO: Change concept of VLAN to concept of Broadcast SwitchMatrix, remove notion on VLAN as RDFObject.

class Vlan(pynt.xmlns.RDFObject):
    "VLAN entry: (number, ports, active)"
    vlanid              = 0     # int
    interfaces          = None  # None  # list (set in __init__) all (logical) interfaces in this VLAN
    adminstatus         = None  # string "up" or "down" or None (unknown)
    
    def __init__(self, identifier, namespace, vlanid):
        # WARNING: A RDFObject should always be created using a [Get]CreateRDFObject() function
        # The init function must never create any other RDFObjects, even not indirectly
        pynt.xmlns.RDFObject.__init__(self, identifier=identifier, namespace=namespace)
        self.setVlanId(vlanid)
        self.interfaces = []
    
    def setVlanId(self,vlanid):
        self.vlanid         = int(vlanid)
        self.setIdentifier("vlan"+str(vlanid))
    def setName(self,name):                         self.name   = str(name)
    def setDescription(self,description):           self.description = str(description)
    
    def getVlanId(self):                            return self.vlanid
    def getName(self):                              return self.name
    def getDescription(self):                       return self.description
    
    def setAdminStatus(self,adminstatus):           self.adminstatus = adminstatus
    def setAllPorts(self,interfacelist):
        if interfacelist == None:
            self.interfaces = []
        elif type(interfacelist) == types.ListType:
            self.interfaces = interfacelist
        else:
            raise TypeError ("Ignoring setAllPorts(list) as the argument is a %s instead of a list" % str(type(labellist)))
            self.interfaces = []
    
    def getAdminStatus(self):                       return self.adminstatus
    def getAllPorts(self):                          return self.interfaces
    
    def addInterface(self,interface):
        if interface not in self.interfaces:
            self.interfaces.append(interface)
    
    def getOtherPorts(self, curinterface=None):
        """returns a list of all interface in of this VLAN, excluding the given interface"""
        # Please note: we create a NEW LIST with all the elements of self.identifiers.
        # This is different from "identifiers = self.identifiers" which really creates a shallow copy
        # (only copies the pointer to the list). Since we delete an element in the list, it MUST NOT be shallow
        interfaces = self.interfaces[:]
        try:
            interfaces.remove(curinterface)
        except ValueError:
            pass;
        return interfaces



class EthernetDevice(pynt.elements.Device):
    """Ethernet device, with knowledge about Ethernet, LANs, VLANs, and MAC layer. 
    Q-in-Q not explicitly supported, though it should be possible to use."""
    vlans               = None  # list (set in __init__)
    nativeInterfaceClass = EthernetInterface
    layer               = None # Set to Ethernet in __init__
    
    def __init__(self, identifier, namespace=None):
        pynt.elements.Device.__init__(self, identifier=identifier, namespace=namespace)
        self.getSwitchMatrix()
        self.vlans = []
        self.layer = GetLayer('ethernet')
    
    def getCreateVlan(self, vlanid, namespace=None):
        """
        Return an Vlan object with the given vlan ID, possible a new object. 
        Note that we return a pointer, so that any changes made to the returned 
        vlan object are reflected in the original vlan list as well. 
        This is what we want.
        """
        if namespace == None:
            namespace = self.getNamespace()
        identifier = VlanIdentifier(vlanid)
        vlan = pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=Vlan, 
                initfunction=self.setNewVlanProperties, vlanid=vlanid)
        # TODO: check if just fetched vlan belongs to this device
        return vlan
    
    def getVlan(self, vlanid, namespace=None):
        """
        Return an existing Vlan object with the given vlan ID. 
        """
        if namespace == None:
            namespace = self.getNamespace()
        identifier = VlanIdentifier(vlanid)
        vlan = pynt.xmlns.GetRDFObject(identifier=identifier, namespace=namespace, klass=Vlan, 
                initfunction=self.setNewVlanProperties, vlanid=vlanid)
        return vlan
    
    def setNewVlanProperties(self, vlan, vlanid=0):
        """Set pre-set values of the new Vlan, before releasing the lock.
        Define all values that must be defined in a valid object"""
        self.vlans.append(vlan)
    
    def getVlans(self):
        """return all vlan objects"""
        return self.vlans
    
    # Note: this model does not support combination of tagged and untagged VLANs at the same
    # interface. If we want to support it, all "untagged" data should be represented as a channel
    # (an internal client interface to be exact), just like each tagged data.
    # However, this yields to problems:
    # 1. The default VLAN contains the interface itself, and that should be replaced with the
    #    channel (logical interface). This is do-able, but requires quite a few special cases,
    #    and we have to keep in mind any existing MAC address adaptations too.
    # 2. There is no way to distinguish between a physical untagged interface (label=None,
    #    untagged=VLANid, tagged=None) and the channel interface (label=None, untagged=VLANid,
    #    tagged=None). However, we can add a "Tagged" channel to the former, but not to the 
    #    later. So it is easier to disallow it all-together.
    
    def AddUntaggedInterface(self, vlan, interface):
        """Assigns an interface to a VLAN, and set the untagged vlanid of the interface
        Produces warning if interface is already tagged, or has another untagged vlanid set."""
        if None != interface.getTaggedVLANids():
            raise pynt.ConsistencyException ("Interface %s is both tagged (VLANs %s) as well as untagged (VLAN %s). This is not supported by the model." % (interface.getName(), interface.getTaggedVLANids(), vlan.getVlanId()))
        curvlan = interface.getUntaggedVLANid()
        if (curvlan != None) and (curvlan != vlan.getVlanId()):
            raise pynt.ConsistencyException ("Interface %s is untagged but seems to be in both VLAN %d as well as VLAN %d." % (interface.getName(), curvlan, vlan.getVlanId()))
        interface.setUntaggedInterface(vlan.getVlanId())
        vlan.addInterface(interface)
    
    def AddTaggedInterface(self, vlan, interface):
        """Assigns an interface to a VLAN, and add the tagged VLAN as an internal client interface to the interface
        Produces a warning if interface is already untagged"""
        if None != interface.getUntaggedVLANid():
            raise pynt.ConsistencyException ("Interface %s is both tagged (VLANs %s) as well as untagged (VLAN %s). This is not supported by the model." % (interface.getName(),  vlan.getVlanId(), interface.getUntaggedVLANid()))
        logicalinterface = interface.addTaggedInterface(vlan.getVlanId())
        vlan.addInterface(logicalinterface)
    
    def getSwitchMatrix(self, layer=None):
        if layer == None:
            layer=GetLayer('ethernet')
        identifier  = self.identifier + "EthernetSwitchMatrix"
        namespace   = self.getNamespace()
        try:
            switchmatrix = pynt.xmlns.GetRDFObject(identifier=identifier, namespace=namespace, klass=pynt.elements.SwitchMatrix)
        except pynt.xmlns.UndefinedNamespaceException:
            switchmatrix = pynt.elements.GetCreateSwitchMatrix(identifier=identifier, namespace=namespace)
            switchmatrix.setLayer(layer)
            switchmatrix.setSwitchingCapability(True)
            switchmatrix.setSwappingCapability(False)
            switchmatrix.setUnicast(False)
            switchmatrix.setBroadcast(True)
            switchmatrix.setDevice(self)
        return switchmatrix

class EthernetSwitchMatrix(pynt.elements.SwitchMatrix):
    def __init__(self, identifier, namespace=None):
        pynt.elements.SwitchMatrix.__init__(self, identifier=identifier, namespace=namespace)
        self.setLayer(GetLayer('ethernet'))
        self.setSwitchingCapability(True)
        self.setSwappingCapability(False)
        self.setUnicast(False)
        self.setBroadcast(True)    
