# -*- coding: utf-8 -*-
"""The TDM module defines a few SONET/SDH specific network element classes"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns
import pynt.technologies.ethernet


# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "tdm"
uri       = 'http://www.science.uva.nl/research/sne/ndl/tdm#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/tdm.rdf'
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
    if shortcut == 'vt15':
        return pynt.layers.GetCreateLayer('VT15NetworkElement', namespace=GetNamespace(), name="VT1.5")
    elif shortcut == 'vt2':
        return pynt.layers.GetCreateLayer('VT2NetworkElement', namespace=GetNamespace(), name="VT2")
    elif shortcut == 'vt3':
        return pynt.layers.GetCreateLayer('VT3NetworkElement', namespace=GetNamespace(), name="VT3")
    elif shortcut == 'vt6':
        return pynt.layers.GetCreateLayer('VT6NetworkElement', namespace=GetNamespace(), name="VT6")
    elif shortcut == 'vtg':
        return pynt.layers.GetCreateLayer('VTGNetworkElement', namespace=GetNamespace(), name="VTG")
    elif shortcut == 'sts1spe':
        return pynt.layers.GetCreateLayer('STS1-SPENetworkElement', namespace=GetNamespace(), name="STS-1 SPE")
    elif shortcut == 'tug3':
        return pynt.layers.GetCreateLayer('TUG3NetworkElement', namespace=GetNamespace(), name="TUG-3")
    elif shortcut == 'vc4':
        return pynt.layers.GetCreateLayer('VC-4NetworkElement', namespace=GetNamespace(), name="VC-4")
    elif shortcut == 'sts3':
        return pynt.layers.GetCreateLayer('STS-3NetworkElement', namespace=GetNamespace(), name="STS-3/AUG-1")
    elif shortcut == 'oc1':
        return pynt.layers.GetCreateLayer('OC1NetworkElement', namespace=GetNamespace(), name="OC-1")
    elif shortcut == 'oc3':
        return pynt.layers.GetCreateLayer('OC3NetworkElement', namespace=GetNamespace(), name="OC-3")
    elif shortcut == 'oc12':
        return pynt.layers.GetCreateLayer('OC12NetworkElement', namespace=GetNamespace(), name="OC-12")
    elif shortcut == 'oc48':
        return pynt.layers.GetCreateLayer('OC48NetworkElement', namespace=GetNamespace(), name="OC-48")
    elif shortcut == 'oc192':
        return pynt.layers.GetCreateLayer('OC192NetworkElement', namespace=GetNamespace(), name="OC-192")
    elif shortcut == 'oc768':
        return pynt.layers.GetCreateLayer('OC768NetworkElement', namespace=GetNamespace(), name="OC-768")
    elif shortcut == 'oc3072':
        return pynt.layers.GetCreateLayer('OC3072NetworkElement', namespace=GetNamespace(), name="OC-3072")
    elif shortcut == 'lambda':
        return pynt.layers.GetCreateLayer('LambdaNetworkElement', namespace=GetNamespace(), name="Lambda")
    elif shortcut == 'fiber':
        return pynt.layers.GetCreateLayer('FiberNetworkElement',  namespace=GetNamespace(), name="Fiber")
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    if name == "WANPHY":
        return pynt.layers.GetCreateAdaptationFunction("WANPHY", namespace=GetNamespace(), clientlayer=pynt.technologies.ethernet.GetLayer('ethernet'), serverlayer=pynt.technologies.tdm.GetLayer('oc192'), clientcount=1, servercount=1, name="WAN PHY")
    else:
        raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("VT15Interface", namespace=GetNamespace(), layer=GetLayer('vt15'))

class VT15Interface(pynt.elements.Interface):
    """VT1.5 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('vt15')


# pynt.elements.GetCreateInterfaceLayer("VT2Interface", namespace=GetNamespace(), layer=GetLayer('vt2'))

class VT2Interface(pynt.elements.Interface):
    """VT2 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('vt2')


# pynt.elements.GetCreateInterfaceLayer("VT3Interface", namespace=GetNamespace(), layer=GetLayer('vt3'))

class VT3Interface(pynt.elements.Interface):
    """VT3 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('vt3')


# pynt.elements.GetCreateInterfaceLayer("VT6Interface", namespace=GetNamespace(), layer=GetLayer('vt6'))

class VT6Interface(pynt.elements.Interface):
    """VT6 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('vt6')


# pynt.elements.GetCreateInterfaceLayer("VTGInterface", namespace=GetNamespace(), layer=GetLayer('vtg'))

class VTGInterface(pynt.elements.Interface):
    """VTG Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('vtg')


# pynt.elements.GetCreateInterfaceLayer("STS1-SPEInterface", namespace=GetNamespace(), layer=GetLayer('sts1spe'))

class STS1SPEInterface(pynt.elements.Interface):
    """STS-1 SPE Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('sts1spe')


# pynt.elements.GetCreateInterfaceLayer("TUG3Interface", namespace=GetNamespace(), layer=GetLayer('tug3'))

class TUG3Interface(pynt.elements.Interface):
    """TUG-3 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('tug3')


# pynt.elements.GetCreateInterfaceLayer("VC-4Interface", namespace=GetNamespace(), layer=GetLayer('vc4'))

class VC4Interface(pynt.elements.Interface):
    """VC-4 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('vc4')


# pynt.elements.GetCreateInterfaceLayer("STS-3Interface", namespace=GetNamespace(), layer=GetLayer('sts3'))

class STS3Interface(pynt.elements.Interface):
    """STS-3/AUG-1 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('sts3')


# pynt.elements.GetCreateInterfaceLayer("OC1Interface", namespace=GetNamespace(), layer=GetLayer('oc1'))

class OC1Interface(pynt.elements.Interface):
    """OC-1 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('oc1')


# pynt.elements.GetCreateInterfaceLayer("OC3Interface", namespace=GetNamespace(), layer=GetLayer('oc3'))

class OC3Interface(pynt.elements.Interface):
    """OC-3 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('oc3')


# pynt.elements.GetCreateInterfaceLayer("OC12Interface", namespace=GetNamespace(), layer=GetLayer('oc12'))

class OC12Interface(pynt.elements.Interface):
    """OC-12 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('oc12')


# pynt.elements.GetCreateInterfaceLayer("OC48Interface", namespace=GetNamespace(), layer=GetLayer('oc48'))

class OC48Interface(pynt.elements.Interface):
    """OC-48 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('oc48')


# pynt.elements.GetCreateInterfaceLayer("OC192Interface", namespace=GetNamespace(), layer=GetLayer('oc192'))

class OC192Interface(pynt.elements.Interface):
    """OC-192 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('oc192')


# pynt.elements.GetCreateInterfaceLayer("OC768Interface", namespace=GetNamespace(), layer=GetLayer('oc768'))

class OC768Interface(pynt.elements.Interface):
    """OC-768 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('oc768')


# pynt.elements.GetCreateInterfaceLayer("OC3072Interface", namespace=GetNamespace(), layer=GetLayer('oc3072'))

class OC3072Interface(pynt.elements.Interface):
    """OC-3072 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('oc3072')


class TDMSwitchDevice(pynt.elements.Device):
    """TDM Cross Connect device, with knowledge about the OC and VC-4 layers only. No knowledge about lower layers."""
    pass

