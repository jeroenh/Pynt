# -*- coding: utf-8 -*-
"""The VPN module defines a few MPLs, L2TP and PPP specific network element classes"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns


# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "vpn"
uri       = 'http://www.science.uva.nl/research/sne/ndl/vpn#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/vpn.rdf'
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
    global uri
    if shortcut == 'ppp':
        return pynt.layers.GetCreateLayer('PPPNetworkElement',   namespace=GetNamespace(), name="PPP")
    elif shortcut == 'l2tp':
        return pynt.layers.GetCreateLayer('L2TPNetworkElement',  namespace=GetNamespace(), name="L2TP")
    elif shortcut == 'mpls':
        return pynt.layers.GetCreateLayer('MPLSNetworkElement',  namespace=GetNamespace(), name="MPLS")
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("PPPInterface", namespace=GetNamespace(), layer=GetLayer('ppp'))

class PPPInterface(pynt.elements.Interface):
    """PPP Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('ppp')


# pynt.elements.GetCreateInterfaceLayer("L2TPInterface", namespace=GetNamespace(), layer=GetLayer('l2tp'))

class L2TPInterface(pynt.elements.Interface):
    """L2TP Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('l2tp')


# pynt.elements.GetCreateInterfaceLayer("MPLSInterface", namespace=GetNamespace(), layer=GetLayer('mpls'))

class MPLSInterface(pynt.elements.Interface):
    """MPLS Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('mpls')

