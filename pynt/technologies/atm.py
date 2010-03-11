# -*- coding: utf-8 -*-
"""The ATM module defines a few ATM specific network element classes: ATMInterface"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns


# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "atm"
uri       = 'http://www.science.uva.nl/research/sne/ndl/atm#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/atm.rdf'
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
    if shortcut == 'aal0':
        return pynt.layers.GetCreateLayer('AAL0NetworkElement', namespace=GetNamespace(), name="AAL0")
    elif shortcut == 'vpinni':
        return pynt.layers.GetCreateLayer('VPI-NNI-LayerNetworkElement', namespace=GetNamespace(), name="VPI (NNI)")
    elif shortcut == 'vpiuni':
        return pynt.layers.GetCreateLayer('VPI-UNI-LayerNetworkElement', namespace=GetNamespace(), name="VPI (UNI)")
    elif shortcut == 'atm':
        return pynt.layers.GetCreateLayer('ATMNetworkElement', namespace=GetNamespace(), name="ATM")
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)
    

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("AAL0Interface", namespace=GetNamespace(), layer=GetLayer('aal0'))

class AAL0Interface(pynt.elements.Interface):
    """AAL0 Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('aal0')
    


# pynt.elements.GetCreateInterfaceLayer("VPI-NNIInterface", namespace=GetNamespace(), layer=GetLayer('vpinni'))

class VPINNILayerInterface(pynt.elements.Interface):
    """VPI (NNI) Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('vpinni')


# pynt.elements.GetCreateInterfaceLayer("VPI-UNIInterface", namespace=GetNamespace(), layer=GetLayer('vpiuni'))

class VPIUNILayerInterface(pynt.elements.Interface):
    """VPI (UNI) Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('vpiuni')


# pynt.elements.GetCreateInterfaceLayer("ATMInterface", namespace=GetNamespace(), layer=GetLayer('atm'))

class ATMInterface(pynt.elements.Interface):
    """ATM Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('atm')


class ATMSwitchDevice(pynt.elements.Device):
    """ATM switch, with knowledge about the ATM, VPI and AAL0 layers."""
    pass

