# -*- coding: utf-8 -*-
"""The IP module defines a few Ethernet specific network element classes: RouterDevice, and IPInterface"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns


# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "ip"
uri       = 'http://www.science.uva.nl/research/sne/ndl/ip#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/ip.rdf'
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
    if shortcut == 'ip':
        return pynt.layers.GetCreateLayer('IPNetworkElement', namespace=GetNamespace(), name="IP")
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("IPInterface", namespace=GetNamespace(), layer=GetLayer('ip'))

class IPInterface(pynt.elements.Interface):
    """IP Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('ip')
        self.ipaddress      = None
        
    def setIPAddress(self, address):
        self.ipaddress = address
    def getIPAddress(self):
        return self.ipaddress
    
    # def setOSPFP2PInterface(self):
    #     self.OSPFP2PInterface = True
    # def setOSPFTEP2PInterface(self):
    #     self.OSPFTEP2PInterface = True

class RouterDevice(pynt.elements.Device):
    """IP router."""
    def __init__(self, *args, **params):
        pynt.elements.Device.__init__(self, *args, **params)
        self.layer          = GetLayer('ip')
        self.nativeInterfaceClass = IPInterface

class IPBroadcastSegment(pynt.elements.BroadcastSegment):
    def __init__(self, *args, **params):
        pynt.elements.BroadcastSegment.__init__(self, *args, **params)
        self.layer          = GetLayer('ip')
