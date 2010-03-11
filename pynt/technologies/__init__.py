# -*- coding: utf-8 -*-
"""Generic technologie package. The functions in here act as an interface to the individual modules. 
You can select the desired technology modules, and load them here. Also, you can ask for a layer 
or technology namespace, based on an URI. This will automatically find and load the appropriate 
technology."""

# standard modules
import types
import os
import os.path
import logging
# local modules
import pynt.elements
import pynt.layers
import pynt.xmlns

def find_all_modules():
    all_files = os.listdir(os.path.dirname(__file__))
    modules = []
    for filename in all_files:
        (root, ext) = os.path.splitext(filename)
        if (ext in ['.py', '.pyc', '.pyo', '.pyw']) and (root not in modules) and (root[0] != "_"):
            modules.append(root)
    return modules

# We can dynamically load all modules in this package.
# Usually, "from pynt.technologies import *" uses the _all_modules variable to find all available 
# We dynamically set this variable.
_all_modules = []
_loaded_modules = []

def add_technology_module(modulename):
    if modulename not in _all_modules:
        _all_modules.append(modulename)

def del_technology_module(modulename):
    global _all_modules
    if modulename in _all_modules:
        _all_modules.remove(modulename)

def import_modules():
    global _all_modules, _loaded_modules
    logger = logging.getLogger("pynt.technologies")
    if len(_loaded_modules) == 0:
        _all_modules = find_all_modules()
        if len(_all_modules) == 0:
            logger.warning("Could not find any technology-specific modules")
    elif len(_loaded_modules) >= len(_all_modules):
        return _loaded_modules
    for modulename in _all_modules:
        module = __import__("pynt.technologies."+modulename, globals(), locals(), "pynt.technologies."+modulename)
        if module not in _loaded_modules:
            _loaded_modules.append(module)
    return _loaded_modules

def GetLayerByPrefix(prefix):
    modules = import_modules()
    for module in modules:
        try:
            return module.GetLayer(prefix)
        except AttributeError:
            pass
    raise AttributeError("Layer with prefix '%s' not found" % (prefix))

#def GetLayerByUri(uri):
#    # uri is e.g. FiberNetworkElement
#    modules = import_modules()
#    for module in modules:
#        for layer in module.layers:
#            if layer.uri == uri:
#                return layer
#    raise AttributeError("Layer with prefix '%s' not found" % (prefix))

def GetTechnologyInterfaces():
    """Given all pynt.technologies.* modules, return a list of all Interface classes."""
    # Note: the pyclbr modules allows us to read the modules and get Interface classes
    # without actually reading the modules. However, that does not set the class.layer 
    # variable as we need later. So we simply have to import all technologies classes.
    interfaceclasses = []
    modules = import_modules()
    for module in modules:
        for var in dir(module):
            attrib = getattr(module, var)
            try:
                if issubclass(attrib, pynt.elements.Interface):
                    interfaceclasses.append(attrib)
            except TypeError:
                pass
    return interfaceclasses

def GetInterfaceClassByLayer(layer):
    interfaceclasses = GetTechnologyInterfaces()
    for interfaceclass in interfaceclasses:
        if interfaceclass.layer == layer:
            return interfaceclass
    raise AttributeError("There is no InterfaceClass with layer '%s'" % str(layer))

# def GetInterfaceClassByUri(uri):
#     # uri is e.g. FiberInterface
#     interfaceclasses = GetTechnologyInterfaces()
#     if len(interfaceclasses) == 0:
#         raise AttributeError("There are no technology-specific modules")
#     for interfaceclass in interfaceclasses:
#         if interfaceclass.layer and (interfaceclass.layer.getURIdentifier() == uri):
#             return interfaceclass
#         if interfaceclass.layer and interfaceclass.layer.getInterfaceLayer().getURIdentifier() == uri:
#             return interfaceclass
#     raise AttributeError("There is no InterfaceClass with uri '%s'" % str(uri))

def GetCreateWellKnownNamespace(prefix=None, uri=None):
    """
    Create a namespace by prefix, by examining the pynt.technologies.* files, 
    and return the appropriate namespace object.
    """
    modules = import_modules()
    namespace = None
    if uri != None:
        for module in modules:
            if module.uri == uri:
                namespace = module.GetNamespace()
                break
        if (prefix != None) and (prefix != namespace.prefix):
            raise AttributeError("The namespace with URI %s has prefix %s instead of %s." % (uri, namespace.prefix, prefix))
    elif prefix != None:
        for module in modules:
            if module.prefix == prefix:
                namespace = module.GetNamespace()
                break
    else:
        raise AttributeError("You need to specify prefix or uri for GetCreateWellKnownNamespace(). They can't be both None.")
    return namespace

