# -*- coding: utf-8 -*-
"""The Copper module defines a few STP/UTP specific network element classes: TwistedPairInterface"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns
import pynt.technologies.ethernet


# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "copper"
uri       = 'http://www.science.uva.nl/research/sne/ndl/copper#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/copper.rdf'
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
    if shortcut == 'utp':
        return pynt.layers.GetCreateLayer('TwistedPairNetworkElement', namespace=GetNamespace(), name="UTP")
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    if name == "base-T":
        return pynt.layers.GetCreateAdaptationFunction("base-T", namespace=GetNamespace(), clientlayer=pynt.technologies.ethernet.GetLayer('ethernet'), serverlayer=pynt.technologies.copper.GetLayer('utp'), clientcount=1, servercount=1, name="1000base-X")
    else:
        raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("TwistedPairInterface", namespace=GetNamespace(), layer=GetLayer('utp'))

class TwistedPairInterface(pynt.elements.Interface):
    """UTP Interface"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('utp')

