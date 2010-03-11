# -*- coding: utf-8 -*-
"""DebugOutput: human readable debugging information. DebugOutput parses all globally defined RDFObjects.
It ignores the subject given to output()"""

# builtin modules
import types
import logging
# local modules
import pynt.xmlns
import pynt.output


def dataattribsortkey(varname):
    primaryvars = ['identifier', 'name', 'namespace', 'nsuri', 'description', # RDF object attributes
            'prefix', 'blade', 'port', 'bladeno', 'vlanid', 'uri',          # identifying attributes
            'layer', 'device', 'labelvalue', 'configured',    # interface attributes
            'interfaces', 'logicalinterfaces', 'blades', 'vlans', 'elements']
    try:
        xpos = primaryvars.index(varname)
        return "%02d%s" % (xpos, varname)
    except ValueError:
        return "%02d%s" % (99, varname)


class DebugOutput(pynt.output.BaseOutput):
    """human readable debugging information"""
    maxdisplaylist      = 8  # do not display lists longer then 8 items; False or None means infinite
    
    def printSubject(self, subject):
        self.write("%s instance %s" % (type(subject).__name__, subject.getURIdentifier()))
        # self.write("%s instance at 0x%x" % (type(subject).__name__, id(subject)))
        variables = dir(subject)   # returns an array of all attributes of the instance, both data attributes and methods
        # varvalues = vars(subject)  # returns a dictionary of data attributes of the instance
        # since a dictionary is not sorted by default, we take care of our own sort.
        # variables = varvalues.keys()
        variables.sort(key=dataattribsortkey)
        # variables.sort()
        for var in variables:
            # value = varvalues[var]
            if var[:2] == "__":
                continue
            value = getattr(subject, var)
            if isinstance(value, types.MethodType):
                continue
            elif isinstance(value, types.NoneType):
                vartype = "None"
            elif isinstance(value, types.BooleanType):
                vartype = "Bool"
            elif isinstance(value, types.ListType):
                vartype = 'list'
                if len(value) == 0:
                    value = "0 items"
                elif self.maxdisplaylist and (len(value) > self.maxdisplaylist):
                    value = str(len(value))+' items'
                else:
                    value = str(sorted(value))
            elif isinstance(value, pynt.xmlns.RDFObject):
                vartype = "rdfobj"
            elif isinstance(value, pynt.xmlns.XMLNamespace):
                vartype = "xmlns"
            elif isinstance(value, types.DictType):
                vartype = 'dict'
                if len(value) == 0:
                    value = "0 items"
                elif self.maxdisplaylist and (len(value) > self.maxdisplaylist):
                    value = str(len(value))+' items'
                else:
                    value = str(sorted(value))
            elif isinstance(value, types.IntType):
                vartype = "int"
            elif isinstance(value, types.LongType):
                vartype = "long"
            elif isinstance(value, types.FloatType):
                vartype = "float"
            elif isinstance(value, types.TupleType):
                vartype = "tuple"
            elif isinstance(value, types.InstanceType):
                vartype = "instnc"
            elif isinstance(value, types.StringTypes):
                vartype = "str"
            elif isinstance(value, types.ClassType):
                vartype = "class"
            elif isinstance(value, types.FileType):
                vartype = "file"
            elif isinstance(value, pynt.rangeset.RangeSet):
                vartype = "range"
            elif isinstance(value, object):
                vartype = "class"
                value = value.__name__
            elif isinstance(value, types.TypeType):
                vartype = "type"
                value = value.__name__
            else:
                vartype = "???"
            self.write("%-24s %-7s %s" % (var+':', vartype, value))
    
    def printNamespaceOverview(self):
        objectcount = 0
        self.write (40 * "=")
        self.write("XML Namespaces:")
        for namespace in pynt.xmlns.GetNamespaces():
            self.write(40 * "-")
            self.printSubject(namespace)
            objectcount += len(namespace.elements)
        self.write(40 * "-")
        self.write("%d objects in %d namespaces" % (objectcount, len(pynt.xmlns.GetNamespaces())))
    
    def printObjectOverview(self):
        objectcount = 0
        classlist = pynt.xmlns.GetRDFClasses(sortkey=classSortKey)
        for klass in classlist:
            self.write (40 * "=")
            self.write("%ss:" % klass.__name__)
            objectlist = pynt.xmlns.GetAllRDFObjects(klass, exactclass=True)
            for rdfobject in objectlist:
                self.write(40 * "-")
                self.printSubject(rdfobject)
            self.write(40 * "-")
            self.write("%d %s objects" % (len(objectlist), klass.__name__))
            objectcount += len(objectlist)
        self.write (40 * "=")
        self.write("%d objects of %d different classes" % (objectcount, len(classlist)))
    
    def output(self, subject=None):
        logger = logging.getLogger("pynt.output")
        if subject != None:
            logger.debug("Ignoring subject parameter for %s" % (type(self).__name__))
        logger.log(25, "Writing %s to %s" % (type(self).__name__, self.filename))
        self.openfile()
        if subject != None:
            self.printSubject(subject)
        else:
            self.printNamespaceOverview()
            self.printObjectOverview()
        self.closefile()


def classSortKey(subject):
    """Sort order: Layers, InterfaceLayers, Adaptations, Device, subclasses of Device (alphabetic), SwitchMatrix, Interface, subclassed of Interface (alphabetic), everything else"""
    if issubclass(subject, pynt.layers.Layer):
        return "1"+subject.__name__
    # elif issubclass(subject, InterfaceLayer):
    #     return "2"+subject.__name__
    elif issubclass(subject, pynt.layers.AdaptationFunction):
        return "3"+subject.__name__
    elif subject == pynt.elements.Device:
        return "4"+subject.__name__
    elif issubclass(subject, pynt.elements.Device):
        return "5"+subject.__name__
    elif issubclass(subject, pynt.elements.SwitchMatrix):
        return "6"+subject.__name__
    elif subject == pynt.elements.Interface:
        return "7"+subject.__name__
    elif issubclass(subject, pynt.elements.ConnectionPoint):
        return "8"+subject.__name__
    else:
        return "9"+subject.__name__

