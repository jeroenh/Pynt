# -*- coding: utf-8 -*-
"""The pynt.layers module defines abstract network functions, like layers and adaptation functions. 
It does not describe actual network elements. See pynt.elements for that."""

# built-in modules
import logging
# local modules
import pynt
import pynt.xmlns
import pynt.rangeset


def GetAdaptationFunction(identifier, namespace):
    """Check if adaptationfunction exists and return the function. Otherwise return None,
    ignoring exceptions (we only check if it exists, we don't want to create it)"""
    try:
       adaptation = pynt.xmlns.GetRDFObject(identifier=identifier, namespace=namespace, klass=AdaptationFunction)
    except pynt.xmlns.UndefinedNamespaceException:
        return None
    return adaptation

def GetAllAdaptationFunctions():
    return pynt.xmlns.GetAllRDFObjects(AdaptationFunction)

def GetCreateAdaptationFunction(identifier, namespace, clientlayer, serverlayer, clientcount=None, servercount=None, name=None, description=None):
    """create a new adaptation with given parameters.
    If an adaptation with the same name exist, check if the properties are the 
    same. If not, raise an exception"""
    adaptationfunction = pynt.xmlns.GetCreateRDFObject(identifier=identifier,namespace=namespace, klass=AdaptationFunction, verifyAttributes=True, clientlayer=clientlayer, serverlayer=serverlayer, clientcount=clientcount, servercount=servercount)
    if name != None:
        adaptationfunction.setName(name)
    if description != None:
        adaptationfunction.setDescription(description)
    return adaptationfunction


class AdaptationFunction(pynt.xmlns.RDFObject):
    "AdaptationFunction entry"
    clientlayer         = None  # Layer object (MUST be set)
    serverlayer         = None  # Layer object (MUST be set)
    clientcount         = None  # integer: max # of allowed client interfaces. None means no limit
    servercount         = None  # integer: max # of allowed server interfaces. None means no limit
    def __init__(self, identifier, namespace, clientlayer, serverlayer, clientcount=None, servercount=None):
        pynt.xmlns.RDFObject.__init__(self, identifier=identifier, namespace=namespace)
        self.setClientLayer(clientlayer)
        self.setServerLayer(serverlayer)
        self.setClientCount(clientcount)
        self.setServerCount(servercount)
        self.namespace.layerschema = True
    
    def setClientLayer(self,clientlayer):
        if not isinstance(clientlayer, Layer):
            raise TypeError("clientlayer must be of type pynt.layers.Layer")
        self.clientlayer = clientlayer
    
    def setServerLayer(self,serverlayer):
        if not isinstance(serverlayer, Layer):
            raise TypeError("serverlayer must be of type pynt.layers.Layer, not %s" % (type(serverlayer).__name__))
        self.serverlayer = serverlayer
    
    def setClientCount(self,clientcount):
        if clientcount == None:
            self.clientcount = None
        else:
            self.clientcount = int(clientcount)
    
    def setServerCount(self,servercount):
        if servercount == None:
            self.servercount = None
        else:
            self.servercount = int(servercount)
    
    def getClientLayer(self):                       return self.clientlayer
    def getServerLayer(self):                       return self.serverlayer
    def getClientCount(self):                       return self.clientcount
    def getServerCount(self):                       return self.servercount
    



def GetCreateLayer(identifier, namespace, name=None, description=None):
    """create a new layer with given parameters.
    If an layer with the same name exist, check if the properties are the 
    same. If not, raise an exception"""
    layer = pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=Layer)
    if name != None:
        layer.setName(name)
    if description != None:
        layer.setDescription(description)
    return layer

def GetAllLayers():
    return pynt.xmlns.GetAllRDFObjects(Layer)


class Layer(pynt.xmlns.RDFObject):
    """network layer"""
    properties          = None # list of all Property instances belonging to this layer, including Property belonging to all layers.
    interfaceuri        = None # instance of ClassURI (unused, was URI that specified a connection point on this specific layer)
    labelprop           = None # instance of Property
    ingresslabelprop    = None # instance of Property
    egresslabelprop     = None # instance of Property
    internallabelprop   = None # instance of Property
    
    def __init__(self, identifier, namespace):
        self.properties = {};
        pynt.xmlns.RDFObject.__init__(self, identifier=identifier, namespace=namespace)
        ndlns = pynt.xmlns.GetCreateWellKnownNamespace("ndl")
        capacityprop = GetCreateProperty("capacity", ndlns, range=float, incompatible=True, compulsory=False)
        self.addProperty(capacityprop)
        self.namespace.layerschema = True

    ######################################
    # Property support (other than labels)
    def addProperty(self, prop):
        name = prop.getIdentifier()
        if name not in self.properties: # not thread safe.
            self.properties[name] = prop
        else:
            logger = logging.getLogger("pynt.elements")
            logger.debug("Property %s is already defined for layer %s. Can't define it again." % (name, self.getName()))
    def setPropertyValue(self, identifier, value):
        """Set a fixed (obligatory) value for a property"""
        try:
            prop = self.properties[identifier]
            prop.setValue(value)
        except KeyError:
            raise KeyError("Can't set value: Property %s is not defined for layer %s" % (propertyname, self.getName()))
        except TypeError:
            raise TypeError("Can't set value: Property %s of layer %s has type %s, value %s has type %s" % (propertyname, self.getName(), prop.range.__name__, value, type(value).__name__))
    def getPropertyValue(self, propertyname):
        try:
            prop = self.properties[propertyname]
            return prop.getValue()
        except KeyError:
            logger = logging.getLogger("pynt.elements")
            logger.debug("Property %s is not defined for layer %s. return None as value" % (propertyname, self.getName()))
            return None
    def hasProperty(self, identifier):
        """Check if the identifier is a property of this layer, to be used
           to check if some dynamic (technology specific) property is valid
           for this layer."""
        if self.properties.has_key(identifier): return True
        return False
    def getProperty(self, identifier):
        if self.properties.has_key(identifier): return self.properties[identifier]
        return None
    # End of property support
    #########################

    def setCapacity(self, capacity):
        self.setPropertyValue("capacity", capacity)
    def getCapacity(self):
        return self.getPropertyValue("capacity")
    # Labelset support
    def labelInLabelProperty(self, label, labelprop):
        if labelprop == None:
            return (label == None) # no label property defined: only None allowed
        elif (label == None):
            return not labelprop.compulsory
        elif labelprop.range.rangeset.isempty(): # empty means no restrictions
            return True
        else:
            return label in labelprop.range.rangeset
    def allowAnyInternalLabel(self):
        """Are there no restrictions for the internal label?"""
        labelprop = self.getInternalLabelProp()
        return (labelprop != None) and labelprop.range.rangeset.isempty()
    def allowNoInternalLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        return (self.getInternalLabelProp() == None)
    def allowNoneInternalLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        labelprop = self.getInternalLabelProp()
        return (labelprop == None) or (not labelprop.compulsory)
    def allowAnyIngressLabel(self):
        """Are there no restrictions for the internal label?"""
        labelprop = self.getIngressLabelProp()
        return (labelprop != None) and labelprop.range.rangeset.isempty()
    def allowNoIngressLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        return (self.getIngressLabelProp() == None)
    def allowNoneIngressLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        labelprop = self.getIngressLabelProp()
        return (labelprop == None) or (not labelprop.compulsory)
    def allowAnyEgressLabel(self):
        """Are there no restrictions for the internal label?"""
        labelprop = self.getEgressLabelProp()
        return (labelprop != None) and labelprop.range.rangeset.isempty()
    def allowNoEgressLabel(self):
        """Is it not allowed to have any label (except the None label?)"""
        return (self.getEgressLabelProp() == None)
    def allowNoneEgressLabel(self):
        """Is the None label allowed (perhaps beside others)?"""
        labelprop = self.getEgressLabelProp()
        return (labelprop == None) or (not labelprop.compulsory)
    def isAllowedLabel(self, label):
        return self.isAllowedInternalLabel(label) and self.isAllowedIngressLabel(label) and self.isAllowedEgressLabel(label)
    def isAllowedIngressLabel(self, label):
        labelprop = self.getIngressLabelProp()
        return self.labelInLabelProperty(label, labelprop)
    def isAllowedEgressLabel(self, label):
        labelprop = self.getEgressLabelProp()
        return self.labelInLabelProperty(label, labelprop)
    def isAllowedInternalLabel(self, label):
        labelprop = self.getInternalLabelProp()
        return self.labelInLabelProperty(label, labelprop)
    def getLabelProp(self):
        return self.labelprop
    def getIngressLabelProp(self):
        if self.ingresslabelprop:
            return self.ingresslabelprop
        else:
            return self.labelprop
    def getEgressLabelProp(self):
        if self.egresslabelprop:
            return self.egresslabelprop
        else:
            return self.labelprop
    def getInternalLabelProp(self):
        if self.internallabelprop:
            return self.internallabelprop
        else:
            return self.labelprop
    def getLabelSet(self):
        """Return the list of labels defined on this layer, taking it from labelset.
        Note that Ethernet is an exception: in there, Ethernet over <anything> MUST have label external None,
        While Ethernet over Ethernet MUST have an external label in the regular range. (0..4095). We can't 
        support this in detail, but perhaps do it partially using compulsory and distinction 
        between internallabelset and egresslabelset."""
        #labelrange = self.getLabelType()
        #if labelrange != None:
        #    return labelrange.rangeset
        if self.labelprop:
            return self.labelprop.range.rangeset
        else:  # layer has no labels defined.
            return pynt.rangeset.RangeSet(None)
    def getIngressLabelSet(self):
        labelprop = self.getIngressLabelProp()
        if labelprop:
            return labelprop.range.rangeset
        else:  # layer has no labels defined.
            return pynt.rangeset.RangeSet(None)
    def getEgressLabelSet(self):
        labelprop = self.getEgressLabelProp()
        if labelprop:
            return labelprop.range.rangeset
        else:  # layer has no labels defined.
            return pynt.rangeset.RangeSet(None)
    def getInternalLabelSet(self):
        labelprop = self.getInternalLabelProp()
        if labelprop:
            return labelprop.range.rangeset
        else:  # layer has no labels defined.
            return pynt.rangeset.RangeSet(None)
    def getLabelType(self):
        """Return the LabelSet associated with this layer by looking through labelsets.
        Returns None is no label was found"""
        if self.labelprop:
            return self.labelprop.range
        elif self.ingresslabelprop:
            return self.ingresslabelprop.range
        elif self.egresslabelprop:
            return self.egresslabelprop.range
        elif self.internallabelprop:
            return self.internallabelprop.range
        else:
            return None
    def hasLabel(self):
        return self.getLabelType() != None
    def hasCompulsoryLabel(self):
        if self.labelprop and self.labelprop.compulsory:
            return True
        elif self.ingresslabelprop and self.ingresslabelprop.compulsory:
            return True
        elif self.egresslabelprop  and self.egresslabelprop.compulsory:
            return True
        elif self.internallabelprop and self.internallabelprop.compulsory:
            return True
        else:
            return False
    def isValidLabelProperty(self, prop):
        """Raises an error if the given property would not be consistent with the current label 
        properties, or with a label property in the first place"""
        curlabeltype = self.getLabelType()
        assert(isinstance(prop, Property))
        assert(isinstance(prop.range, LabelSet)) # or prop.range in [int, str])
        if not prop.incompatible:
            raise pynt.ConsistencyException ("Label property %s must have incompatible flag set to True." % (prop))
        elif curlabeltype not in [None, prop.range]:
            raise pynt.ConsistencyException ("Can't set label property %s with labelset %s: The labelset of layer %s is already set to %s" % (prop, prop.range, self.getName(), curlabeltype))
        return True
    def setLabelProperty(self, prop):
        if self.isValidLabelProperty(prop): # raises exception if not
            if self.labelprop not in [prop, None]:
                raise pynt.ConsistencyException("Layer %s has label property %s, can not override it to %s" % (self, self.labelprop, prop))
            self.labelprop = prop
    def setIngressLabelProperty(self, prop):
        if self.isValidLabelProperty(prop): # raises exception if not
            if self.ingresslabelprop not in [prop, None]:
                raise pynt.ConsistencyException("Layer %s has ingress label property %s, can not override it to %s" % (self, self.ingresslabelprop, prop))
            self.ingresslabelprop = prop
    def setEgressLabelProperty(self, prop):
        if self.isValidLabelProperty(prop): # raises exception if not
            if self.egresslabelprop not in [prop, None]:
                raise pynt.ConsistencyException("Layer %s has egress label property %s, can not override it to %s" % (self, self.egresslabelprop, prop))
            self.egresslabelprop = prop
    def setInternalLabelProperty(self, prop):
        if self.isValidLabelProperty(prop): # raises exception if not
            if self.internallabelprop not in [prop, None]:
                raise pynt.ConsistencyException("Layer %s has internal label property %s, can not override it to %s" % (self, self.internallabelprop, prop))
            self.internallabelprop = prop
    # FIXME: this function should be removed after it is implemented in the RDF devicefetcher
    def setRDFProperty(self, predicate, value):
        # logger = logging.getLogger("pynt.elements")
        if str(predicate) == pynt.xmlns.GetCreateWellKnownNamespace("ndl")["capacity"]:
            self.setCapacity(value)
        else:
            super(Layer, self).setRDFProperty(predicate, value)
    def getRDFProperty(self, predicate):
        # logger = logging.getLogger("pynt.elements")
        if str(predicate) == pynt.xmlns.GetCreateWellKnownNamespace("ndl")["capacity"]:
            return self.getCapacity()
        else:
            super(Layer, self).getRDFProperty(predicate)
    
    # TODO: add Label URI, type, range information
    # There may be 5 URI: Label class, label predicate, internal label predicate, ingress label predicate, egress label predicate
    
    # TODO: add layer property information, and perhaps other 
    
    # interfacelayer  = None # RDFObject or none; interface at a layer; subclass of Layer and of Interface
    # def getInterfaceLayer(self):
    #     if self.interfacelayer:
    #         return self.interfacelayer
    #     # If there is no InterfaceLayer, we create one in the same namespace, renaming
    #     # MylayerNetworkElement to MylayerInterface
    #     identifier = self.getIdentifier()
    #     if identifier.endswith("NetworkElement"):
    #         identifier = identifier[:-14] + "Interface"
    #     else:
    #         identifier = identifier + "Interface"
    #     return identifier
    #     namespace   = self.getNamespace()
    #     interfacelayer = GetCreateInterfaceLayer()
    #     GetCreateInterfaceLayer(identifier=identifier, namespace=namespace, layer=self)
    #     self.setInterfaceLayer(interfacelayer)
    #     return interfacelayer
    # def setInterfaceLayer(self, interfacelayer):
    #     self.interfacelayer = interfacelayer
    #     if not interfacelayer.layer:
    #         interfacelayer.layer = self

def GetCreateProperty(identifier, namespace=None, range=int, incompatible=False, compulsory=False):
    """create a new property with given parameters.
    If a property with the same name exist, check if the properties are the 
    same. If not, raise an exception"""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=Property, range=range, incompatible=incompatible, compulsory=compulsory)


class Property(pynt.xmlns.RDFObject):
    """A predicate belonging to a layer, with URI and range"""
    range       = None  # None, int, float, bool, str, RangeSet, set instance, RangeSet instance, LabelSet instance, or ResourceClass instance
    # int, float, bool, str and RangeSet do not have an associated URI for the type.
    # LabelSet and ResourceClass do have an associated URI for the type.
    # int, float, bool, str, RangeSet means that a value of this property must be resp. int, float, bool or string or RangeSet instance (the last one is uncommon by the way).
    # ResourceClass, set or RangeSet instance means that a value of this property must be in the given set or range.
    incompatible = False # if True, two connections points which disjoint values of this properties can not exchange data.
    compulsory   = False # if True, a connection point MUST define a value for this property
    # MUST be the same for two connections points communicate with each other, or 
    # in the case of a range, like packet size, there must be an overlap.
    value        = None  # Optional parameter, specifying obligatory property values.
    optimalrange = (None, None) # Optimal minimal and maximal value of range
    def __init__(self, identifier, namespace, range, incompatible=False, compulsory=False):
        # Range has to be either a class or an instance of Rangeset or Resourceclass
        assert (type(range) == type) or (range == None) or isinstance(range, (pynt.rangeset.RangeSet, pynt.layers.LabelSet, ResourceClass, set)) , "range is %s (type: %s)" % (range,type(range))
        self.range = range
        self.incompatible = incompatible
        self.compulsory = compulsory
        pynt.xmlns.RDFObject.__init__(self, identifier, namespace=namespace)
        self.namespace.layerschema = True
    def setValue(self, value):
        """Warning: this is only to set a fixed value for all properties at a certain layer (e.g. all OC-192 have 9.5Gb/s as capacity)"""
        if type(self.range) == type: # range is int, float, bool, str, RangeSet instance, set instance, etc.
            if not isinstance(value, self.range):
                value = self.range(value)
        elif type(self.range) == set:
            if value not in self.range:
                raise ValueError("value %s of property %s not in set %s" % (value, self.getName(), self.range))
        elif isinstance(self.range, pynt.rangeset.RangeSet):
            if not isinstance(value, self.range.itemtype):
                value = self.range.itemtype(value)
            if value in self.range:
                raise ValueError("value %s of property %s not in range %s" % (value, self.getName(), self.range))
        elif isinstance(self.range, ResourceClass):
            if not isinstance(value, Resource):  # value must be a Resource URI.
                value = str(value)
        elif self.range == None:
            pass
        else:
            raise AssertionError("Unknown range %s of property %s" % self.range, self.getName())
        self.value = value
    def getValue(self):
        return self.value
    # def __str__(self):
    #     cardinality = (self.compulsory and "compulsory" or "optional")
    #     return '<%s %s %s>' % (type(self).__name__, self.identifier, cardinality, self.range)
    def setOptimalRange(self, min, max):
        """Sets the optimal range values for this property if applicable."""
        if min != None and type(min) != self.range:
           raise AssertionError("Optimal range minimum %s is not of range type %s" % (min, self.range))
        if max != None and type(max) != self.range:
           raise AssertionError("Optimal range maximum %s is not of range type %s" % (max, self.range))
        self.optimalrange = (min, max)
    def getOptimalRange(self):
        return self.optimalrange

def GetCreateLabelSet(identifier, namespace, rangeset):
    """create a new property with given parameters, or return existing one if it already exists."""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=LabelSet, rangeset=rangeset)


class LabelSet(pynt.xmlns.RDFObject):
    """A data type, specifying a subset of integers or floats with associate URI to identify this type.
    For example, #VLAN tag, which are a subset of integers, in the 0...4095 range."""
    # WARNING: do not make LabelSet a direct subclass of RangeSet. Otherwise, comparing two
    # LabelSet which accidentially have the same values are considered equal.
    rangeset     = None   # the rangeset
    def __init__(self, identifier, namespace, rangeset):
        pynt.xmlns.RDFObject.__init__(self, identifier, namespace=namespace)
        self.rangeset = rangeset
        # not sure where a LabelSet belongs.
        # self.namespace.networkschema = True
        # self.namespace.layerschema = True


def GetCreateResourceClass(identifier, namespace=None):
    """create a new property with given parameters, or return existing one if it already exists."""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=ResourceClass)


class ResourceClass(pynt.xmlns.RDFObject):
    """A generic data type, specified as a list of possible values. Each possible value is in fact a URI.
    For example, #Cladding with possible values #SingleMode and #MultiMode."""
    resourcelist = None
    def __init__(self, identifier, namespace):
        pynt.xmlns.RDFObject.__init__(self, identifier, namespace=namespace)
        self.resourcelist = []
        self.namespace.layerchema = True
    def addKnownResource(self, resource):
        if resource not in self.resourcelist:
            self.resourcelist.append(resource)
    def getKnownResources(self):
        return self.resourcelist


def GetCreateResource(identifier, namespace=None):
    """create a new property with given parameters, or return existing one if it already exists."""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=Resource)


class Resource(pynt.xmlns.RDFObject):
    """A possible value of a layer property. Always a URI. For example #SingleMode (for cladding)"""
    def __init__(self, identifier, namespace):
        pynt.xmlns.RDFObject.__init__(self, identifier, namespace=namespace)
        # self.namespace.layerchema = True  # not a layer schema, nor a network schema, really.


def GetCreateClassURI(identifier, namespace=None):
    """create a new property with given parameters, or return existing one if it already exists."""
    return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=ClassURI)


class ClassURI(pynt.xmlns.RDFObject):
    """A URI identifying a class, for example the URI identifying an FiberInterface, which 
    is a subClassOf Interface as well as a subClassOf NetworkElement."""
    def __init__(self, identifier, namespace):
        pynt.xmlns.RDFObject.__init__(self, identifier, namespace=namespace)
        self.namespace.layerchema = True


# def GetCreateInterfaceLayer(identifier, namespace=None, layer=None):
#     """create a new adaptation with given parameters.
#     If an adaptation with the same name exist, check if the properties are the 
#     same. If not, raise an exception"""
#     if layer and not namespace:
#         namespace = layer.getNamespace()
#     return pynt.xmlns.GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=InterfaceLayer, layer=layer)
# 
# 
# class InterfaceLayer(pynt.xmlns.RDFObject):
#     """Interface type at a certain layer. subclass of Layer and of Interface"""
#     layer           = None # RDFObject or none
#     def __init__(self, identifier, namespace, layer=None):
#         pynt.xmlns.RDFObject.__init__(self, identifier=identifier, namespace=namespace)
#         if layer:
#             self.setLayer(layer)
#     def setLayer(self, layer):
#         self.layer = layer
#         if not layer.interfacelayer:
#             layer.interfacelayer = self
#     def getLayer(self):                 return self.layer


