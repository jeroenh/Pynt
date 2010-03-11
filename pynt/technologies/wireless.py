# -*- coding: utf-8 -*-
"""The Wirelss module defines a few 802.11 specific network element classes: IEEE80211Interface"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns


# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "wireless"
uri       = 'http://www.science.uva.nl/research/sne/ndl/wireless#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/wireless.rdf'
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
    if shortcut == 'ieee80211':
        return pynt.layers.GetCreateLayer('IEEE802-11NetworkElement', namespace=GetNamespace(), name="802.11")
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("IEEE802-11Interface", namespace=GetNamespace(), layer=GetLayer('ieee80211'))

class IEEE80211Interface(pynt.elements.Interface):
    """802.11 wireless Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('ieee80211')

