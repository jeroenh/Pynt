# -*- coding: utf-8 -*-
"""The Bundle module defines a few Ethernet specific network element classes: BundleInterface"""

# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns


# ns and layers variables and GetCreateWellKnownAdaptationFunction() functions are always present in the pynt.technologies.* files.

prefix    = "bundle"
uri       = 'http://www.science.uva.nl/research/sne/ndl/bundle#'
schemaurl = 'http://www.science.uva.nl/research/sne/schema/bundle.rdf'
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
    if shortcut == 'bundle':
        return pynt.layers.GetCreateLayer('BundleNetworkElement', namespace=GetNamespace(), name="Bundle")
    else:
        raise AttributeError("Unknown layer '%s'" % shortcut)

def GetCreateWellKnownAdaptationFunction(name):
    global uri
    raise AttributeError("Adaptation Function '%s' unknown in namespace %s" % (name, uri))


# pynt.elements.GetCreateInterfaceLayer("BundleInterface", namespace=GetNamespace(), layer=GetLayer('bundle'))

class BundleInterface(pynt.elements.Interface):
    """Bundle Interface: A duct"""
    def __init__(self, *args, **params):
        pynt.elements.Interface.__init__(self, *args, **params)
        self.layer          = GetLayer('bundle')

