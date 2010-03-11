# -*- coding: utf-8 -*-
"""The WDM module defines a few Ethernet specific network element classes: OXCDevice, LambdaInterface and FiberInterface"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns
import pynt.technologies.tdm
import pynt.technologies.ethernet


# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "wdm"
uri       = 'http://www.science.uva.nl/research/sne/ndl/wdm#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/wdm.rdf'
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
    if shortcut == 'lambda':
        try:
            return pynt.xmlns.GetRDFObject("LambdaNetworkElement", namespace=GetNamespace(), klass=pynt.layers.Layer)
        except pynt.xmlns.UndefinedNamespaceException, e:
            layer = pynt.layers.GetCreateLayer('LambdaNetworkElement', namespace=GetNamespace(), name="Lambda")
            rangeset = pynt.rangeset.RangeSet("750.0-1700.0", itemtype=float, interval=0.1)  # TODO: set interval dynamically
            rangeset = pynt.layers.GetCreateLabelSet("WavelengthLabel", GetNamespace(), rangeset)
            labelprop = pynt.layers.GetCreateProperty("wavelength", GetNamespace(), rangeset, incompatible=True, compulsory=True)
            layer.setLabelProperty(labelprop)
            return layer
    elif shortcut == 'fiber':
        return pynt.layers.GetCreateLayer('FiberNetworkElement',  namespace=GetNamespace(), name="Fiber")
        try:
            return pynt.xmlns.GetRDFObject("FiberNetworkElement", namespace=GetNamespace(), klass=pynt.layers.Layer)
        except pynt.xmlns.UndefinedNamespaceException, e:
            layer = pynt.layers.GetCreateLayer('FiberNetworkElement', namespace=GetNamespace(), name="Fiber")
            rangeset = pynt.rangeset.RangeSet(None, itemtype=int, interval=1)  # None means "everything allowed", even strings
            rangeset = pynt.layers.GetCreateLabelSet("StrandLabel", pynt.technologies.bundle.GetNamespace(), rangeset)
            labelprop = pynt.layers.GetCreateProperty("strand", GetNamespace(), rangeset, incompatible=True, compulsory=False)
            layer.setLabelProperty(tagprop)
            return layer
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    if name == "WDM":
        return pynt.layers.GetCreateAdaptationFunction("WDM", namespace=GetNamespace(), clientlayer=pynt.technologies.wdm.GetLayer('lambda'), serverlayer=pynt.technologies.wdm.GetLayer('fiber'), clientcount=None, servercount=1, name="WDM")
    elif name == "oc192-in-Lambda":
        return pynt.layers.GetCreateAdaptationFunction("oc192-in-Lambda", namespace=GetNamespace(), clientlayer=pynt.technologies.tdm.GetLayer('oc192'), serverlayer=pynt.technologies.wdm.GetLayer('lambda'), clientcount=1, servercount=1, name="OC-192 in Lambda")
    elif name == "eth1000base-X":
        return pynt.layers.GetCreateAdaptationFunction("eth1000base-X", namespace=GetNamespace(), clientlayer=pynt.technologies.ethernet.GetLayer('ethernet'), serverlayer=pynt.technologies.wdm.GetLayer('lambda'), clientcount=1, servercount=1, name="1000base-X")
    elif name == "eth10Gbase-R":
        return pynt.layers.GetCreateAdaptationFunction("eth10Gbase-R", namespace=GetNamespace(), clientlayer=pynt.technologies.ethernet.GetLayer('ethernet'), serverlayer=pynt.technologies.wdm.GetLayer('lambda'), clientcount=1, servercount=1, name="10Gbase-R")
    else:
        raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("LambdaInterface", namespace=GetNamespace(), layer=GetLayer('lambda'))

class LambdaInterface(pynt.elements.Interface):
    """Lambda Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('lambda')
    
    def setWavelenght(self, wavelength):        self.setLabel(wavelength)
    def getWavelenght(self):                    self.getEgressLabel()


# pynt.elements.GetCreateInterfaceLayer("FiberInterface", namespace=GetNamespace(), layer=GetLayer('fiber'))

class FiberInterface(pynt.elements.Interface):
    """Fiber Interface"""
    spacing             = None  # string or None
    cladding            = None  # string or None
    polish              = None  # string or None
    connector           = None  # string or None
    transceiver         = None  # string or None
    egresspower         = None  # float (transmitted power level in dBm, with 0 dBm = 1 mWatt) or None (unknown)
    ingresspower        = None  # float (received power level in dBm, with 0 dBm = 1 mWatt) or None (unknown)
    device              = None
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('fiber')
    
    def setSpacing(self, spacing):              self.spacing = spacing
    def setCladding(self, cladding):            self.cladding = cladding
    def setPolish(self, polish):                self.polish = polish
    def setTransceiver(self, transceiver):      self.transceiver = transceiver
    def setConnector(self, connector):          self.connector = connector
    def setEgressPowerLevel(self, powerlevel):  self.egresspower = float(powerlevel)
    def setIngressPowerLevel(self, powerlevel): self.ingresspower = float(powerlevel)
    def getSpacing(self):                       return self.spacing
    def getCladding(self):                      return self.cladding
    def getPolish(self):                        return self.polish
    def getTransceiver(self):                   return self.transceiver
    def getConnector(self):                     return self.connector
    def getEgressPowerLevel(self):              return self.egresspower
    def getIngressPowerLevel(self):             return self.ingresspower
    def getSpacingURI(self):
        ns = GetNamespace()
        if not self.spacing:
            return None
        elif self.spacing.startswith("http"):
            return self.spacing
        else:
            return ns.uri+self.spacing
    def getCladdingURI(self):
        ns = GetNamespace()
        if not self.cladding:
            return None
        elif self.cladding.startswith("http"):
            return self.cladding
        else:
            return ns.uri+self.cladding
    def getPolishURI(self):
        ns = GetNamespace()
        if not self.polish:
            return None
        elif self.polish.startswith("http"):
            return self.polish
        else:
            return ns.uri+self.polish
    def getTransceiverURI(self):
        ns = GetNamespace()
        if not self.transceiver:
            return None
        elif self.transceiver.startswith("http"):
            return self.transceiver
        else:
            return ns.uri+self.transceiver
    def getConnectorURI(self):
        ns = GetNamespace()
        if not self.connector:
            return None
        elif self.connector.startswith("http"):
            return self.connector
        else:
            return ns.uri+self.connector+"-Connector"
    
    def setRDFProperty(self, predicate, value):
        ns = GetNamespace()
        if str(predicate) == ns["ingressPowerLevel"]:
            self.setIngressPowerLevel(value)
        elif str(predicate) == ns["egressPowerLevel"]:
            self.setEgressPowerLevel(value)
        elif str(predicate) == ns["spacing"]:
            (namespace, identifier) = pynt.xmlns.splitURI(value)
            if namespace == ns:
                self.setSpacing(identifier)
            else:
                self.setSpacing(value)
        elif str(predicate) == ns["cladding"]:
            (namespace, identifier) = pynt.xmlns.splitURI(value)
            if namespace == ns:
                self.setCladding(identifier)
            else:
                self.setCladding(value)
        elif str(predicate) == ns["polish"]:
            (namespace, identifier) = pynt.xmlns.splitURI(value)
            if namespace == ns:
                self.setPolish(identifier)
            else:
                self.setPolish(value)
        elif str(predicate) == ns["transceiver"]:
            (namespace, identifier) = pynt.xmlns.splitURI(value)
            if namespace == ns:
                self.setTransceiver(identifier)
            else:
                self.setTransceiver(value)
        elif str(predicate) == ns["connector"]:
            (namespace, identifier) = pynt.xmlns.splitURI(value)
            if namespace == ns:
                self.setConnector(identifier)
            else:
                self.setConnector(value)
        else:
            super(FiberInterface, self).setRDFProperty(predicate, value)
    
    def getRDFProperty(self, predicate):
        ns = GetNamespace()
        if str(predicate) == ns["ingressPowerLevel"]:
            return self.getIngressPowerLevel()
        elif str(predicate) == ns["egressPowerLevel"]:
            return self.getEgressPowerLevel()
        elif str(predicate) == ns["spacing"]:
            return self.getSpacingURI()
        elif str(predicate) == ns["cladding"]:
            return self.getCladdingURI()
        elif str(predicate) == ns["polish"]:
            return self.getPolishURI()
        elif str(predicate) == ns["transceiver"]:
            return self.getTransceiverURI()
        elif str(predicate) == ns["connector"]:
            return self.getConnectorURI()
        else:
            super(FiberInterface, self).getRDFProperty(predicate)


class OXCDevice(pynt.elements.Device):
    """Optical Cross Connect device, with knowledge about the Fiber layer only."""
    nativeInterfaceClass = FiberInterface
    def __init__(self, identifier, namespace=None):
        pynt.elements.Device.__init__(self, identifier=identifier, namespace=namespace)
        self.getSwitchMatrix()
    
    def getSwitchMatrix(self, layer=None):
        if layer == None:
            layer = GetLayer('fiber')
        identifier  = "FiberSwitchMatrix"
        namespace   = self.getNamespace()
        try:
            switchmatrix = pynt.xmlns.GetRDFObject(identifier=identifier, namespace=namespace, klass=pynt.elements.SwitchMatrix)
        except pynt.xmlns.UndefinedNamespaceException:
            switchmatrix = pynt.elements.GetCreateSwitchMatrix(identifier=identifier, namespace=namespace)
            switchmatrix.setLayer(layer)
            switchmatrix.setSwitchingCapability(True)
            switchmatrix.setSwappingCapability(True)
            switchmatrix.setUnicast(True)
            switchmatrix.setMulticast(False)
            switchmatrix.setDevice(self)
        return switchmatrix


class WSSDevice(pynt.elements.Device):
    """Wavelength selective switch, with knowledge about the Lambda and Fiber layer."""
    pass

