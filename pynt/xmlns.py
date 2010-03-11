# -*- coding: utf-8 -*-
"""
A helper module for XML stuff, handling identifiers, namespaces, and prefixes.
xmlns keeps a global repository of all RDFObject instances (e.g. Devices, Interfaces)
and makes sure the namespace + identifier combination is unique. The module is thread-safe,
as long as RDFObject (or their subclasses) are never directly created, but only 
using the functions GetRDFObjcet, GetCreateRDFObject, CreateObject and GetCreateNamespace.
"""

# built-in modules
import types
import re
import threading    # for lock object for thread safety
import logging
import time
# import sys          # for sys.referencecount()
# import distutils.version
# local modules
import pynt


# This file should explicitly does not depend on the rdflib.* classes.
# Two reasons:
# * We do not depend on external libraries
# * We implement a singleton design pattern: there can be only one RDF Object with a given name
# Extending rdflib to implement the later would be highly non-trivial, if we do not want to 
# modify code in the rdflib itself.

class UndefinedNamespaceException(Exception):
    "Raised when no namespace is found with given property"
    pass


class DuplicateNamespaceException(Exception):
    "Raised when no namespace is found with given property"
    pass


# global lock object for this module, shared among all threads.
# object creation
threadlock = threading.Lock()
logger = logging.getLogger("pynt.xmlns")
logger.debug("Created global lock object %s" % threadlock)


def splitURI(uri):
    """Split the URI of a subject into a namespace and a identifier part"""
    pos = uri.rfind('#')
    if pos >= 0:
        base = uri[:pos+1]
        identifier = uri[pos+1:]
    else: 
        base = uri
        identifier = ""
        # pos = uri[9:].rfind('/')  # start from char 9 to skip the / in http(s)://
        # if pos >= 0:
        #     base = uri[:pos+10]
        #     identifier = uri[pos+10:]
        # else:
        #     base = uri
        #     identifier = ""
    namespace = GetCreateNamespace(base)
    return (namespace,identifier)


# singleton design pattern

rdfobjects = {}     # dict, sorted by class, pointing to a list of RDF objects of that class


class RDFObject(object):
    """XML/RDF object, identified by a namespace+identifier"""
    identifier          = ""    # string, MUST be non empty (set in __init__); local to namespace
    name                = ""    # string, with rdfs:label
    namespace           = None  # namespace object; MUST be non empty (set in __init__)
    description         = ""    # string
    sources             = None  # list of seeAlso URIs
    
    class __metaclass__(type):
        def __call__(cls, *args, **kwargs):
            # override the metaclass to only call __new__ (default is __new__ and __init__)
            return cls.__new__(cls, *args, **kwargs)
    
    def __new__(klass, identifier, namespace, *args, **kwargs):
        """Override new to make sure only ONE unique RDFObject with the same URI can 
        exist at the same time. Since we also override __metaclass__, a second instantiation
        does NOT call __init__ again."""
        assert(isinstance(namespace, XMLNamespace))
        identifier = UTF8(identifier)
        if identifier not in namespace.elements:
            logger = logging.getLogger("pynt.xmlns")
            logger.debug("Creating %s object %s in namespace %s" % (klass.__name__, identifier, namespace.getURI()))
            global threadlock
            # we do the thread-safe part in two stages:
            # first we do a quick global lock, and create a "lock" for this object only
            # we then release the global lock, and create the new object using the object-specific lock.
            # start global lock (only called if identifier did not exist, so not too often)
            threadlock.acquire()
            # check if it still doesn't exist (another thread may have created it in the last few miliseconds)
            if identifier not in namespace.elements:
                # None means: it's not there yet, but we're creating it. Other threads: stay off and wait till we assign it
                namespace.elements[identifier] = None
                threadlock.release() # end global lock.
                # create a new object, and call __init__.
                xmlobject = object.__new__(klass)
                #klass.__init__(xmlobject, identifier, namespace, *args, **kwargs)
                xmlobject.__init__(identifier, namespace, *args, **kwargs)
                if not hasattr(xmlobject, 'rdfobject_initfunction_wascalled'):
                    raise pynt.ConsistencyException("The __init__ function of %s did not call the parent __init__ function in RDFObject" % (klass.__name__))
                del xmlobject.rdfobject_initfunction_wascalled
                global rdfobjects
                if klass not in rdfobjects:
                    rdfobjects[klass] = []
                threadlock.acquire() # second short global lock; probably not needed though
                if xmlobject not in rdfobjects[klass]:
                    rdfobjects[klass].append(xmlobject)
                namespace.elements[identifier] = xmlobject
                threadlock.release() # end lock
                logger.info("Created  %s object %s in namespace %s" % (type(xmlobject).__name__, identifier, namespace.getURI()))
            else:
                threadlock.release()
                logger.debug("Object creation lock released")
        xmlobject = namespace.elements[identifier]
        if xmlobject == None:
            # Another thread is in the process of creating the object
            logger = logging.getLogger("pynt.xmlns")
            logger.debug("Wait for other thread to create object %s in namespacce %s" % (identifier, namespace.getURI()))
            end_time = time.time() + 10 # 10 second time-out
            while namespace.elements[identifier] == None:
                if time.time() > end_time:
                    raise DuplicateNamespaceException("An other thread claims to create object %s in namespace %s, but after 10 seconds, it still doesn't exist." % (identifier, namespace.getURI()))
                    break
                time.sleep(0.05)
            logger.debug("Got newly created object %s in namespace %s" % (identifier, namespace.getURI()))
            xmlobject = namespace.elements[identifier]
        if klass and not isinstance(xmlobject,klass):
            raise UndefinedNamespaceException("Object %s in namespace %s is a %s, instead of a %s" % (identifier, namespace.getURI(), type(xmlobject).__name__, klass.__name__))
        return xmlobject
    
    def __init__(self, identifier, namespace):
        assert (namespace != None)
        assert (isinstance(namespace, XMLNamespace))
        self.identifier = identifier
        self.namespace  = namespace
        self.sources = []
        self.rdfProperties = {}
        self.rdfobject_initfunction_wascalled = True
    
    def __str__(self): # normal program output (no "" around strings)
        return '<%s %s>' % (type(self).__name__, self.identifier)
    def __repr__(self): # debugging output ("" around string to distinguish "2" from 2)
        return '<%s %s>' % (type(self).__name__, self.identifier)
        # return '<%s object %s at 0x%x>' % (type(self).__name__, self.identifier, id(self))
    
    # def __cmp__(self, value):
    #     """x.__cmp__(y) <==> cmp(x,y)."""
    #     if not isinstance(value, RDFObject):
    #         return -1
    #     comp = cmp(self.namespace.getURI(), value.namespace.getURI())
    #     if comp == 0:
    #         return cmp(self.identifier, value.identifier)
    #     else:
    #         return comp
    
    def setIdentifier(self,identifier):
        identifier = UTF8(identifier)
        if identifier != self.identifier:
            assert (self.namespace != None)
            if self.identifier:
                del self.namespace.elements[self.identifier]
            self.identifier = identifier
            if identifier in self.namespace.elements:
                raise DuplicateNamespaceException("An other %s object with identifier %s already exists in namespace %s" % 
                        (type(self.namespace.elements[identifier]).__name__, identifier, self.namespace.getURI()))
            self.namespace.elements[identifier] = self
    
    def setNamespace(self,namespace):
        if namespace == self.namespace:
            return
        if not isinstance(namespace, XMLNamespace):
            raise TypeError("Namespace must be of type pynt.xmlns.XMLNamespace")
        else:
            if self.identifier:
                if self.namespace:
                    del self.namespace.elements[self.identifier]
                if self.identifier in namespace.elements:
                    raise DuplicateNamespaceException("An other %s object with identifier %s already exists in namespace %s" % 
                        (type(namespace.elements[self.identifier]).__name__, self.identifier, namespace.uri))
                namespace.elements[self.identifier] = self
            self.namespace = namespace
    
    def setName(self,name):                         self.name = UTF8(name)
    def setDescription(self,description):           self.description = UTF8(description)
    def getIdentifier(self):                        return self.identifier
    def getNamespace(self):                         return self.namespace
    def getName(self): # the rdfs:label
        if self.name == "":
            return self.getIdentifier()
        else:
            return self.name
    def getDescription(self):                       return self.description
    def getURIdentifier(self):                      return self.namespace.getURI()+self.getIdentifier()
    def getXMLEltIdentifier(self):                  return self.namespace.getPrefix()+':'+self.getIdentifier()
    
    def attachSource(self, url):
        """Add a related (seeAlso) source to a subject. The given URL will NOT be fetched automatically."""
        if url not in self.sources:
            self.sources.append(url)
    def getSources(self):
        return self.sources
    
    def addRDFProperty(self, ns, predicate, value):
        self.rdfProperties[(ns,predicate)] = value
    def getRDFProperty(self,ns,predicate):
        return self.rdfProperties[(ns,predicate)]
    def hasRDFProperty(self,ns,predicate):
        return self.rdfProperties.has_key((ns,predicate))
    def getRDFProperties(self):
        out = []
        for (ns,predicate) in self.rdfProperties.keys():
            value = self.rdfProperties[(ns,predicate)]
            out.append((ns,predicate,value))
        return out
        
    # # FIXME: this function should be removed after it is implemented in the RDF devicefetcher
    def setRDFProperty(self, predicate, value):
        if str(predicate) in [  "http://www.science.uva.nl/research/sne/ndl#name",
                                "http://www.w3.org/2000/01/rdf-schema#label", ]:
            self.setName(value)
        elif str(predicate) in ["http://www.science.uva.nl/research/sne/ndl#description",
                                "http://www.w3.org/2000/01/rdf-schema#comment",
                                "http://purl.org/dc/elements/1.1/#description", ]:
            self.setDescription(value)
        else:
            #print "-> setting property %s" % predicate
            raise UndefinedNamespaceException("predicate %s unknown for %s %s." % (predicate, type(self), self.getURIdentifier()))
    
    # def getRDFProperty(self, predicate):
    #     if str(predicate) in [  "http://www.science.uva.nl/research/sne/ndl#name",
    #                             "http://www.w3.org/2000/01/rdf-schema#label", ]:
    #         return self.getName()
    #     elif str(predicate) in ["http://www.science.uva.nl/research/sne/ndl#description",
    #                             "http://www.w3.org/2000/01/rdf-schema#comment",
    #                             "http://purl.org/dc/elements/1.1/#description", ]:
    #         return self.getDescription()
    #     else:
    #         raise UndefinedNamespaceException("predicate %s unknown for %s %s." % (predicate, type(self), self.getURIdentifier()))


def RDFObjectExists(identifier, namespace=None):
    try:
        GetRDFObject(identifier=identifier, namespace=namespace)
    except UndefinedNamespaceException:
        return False
    else: 
        return True

def GetCreateRDFObject(identifier, namespace=None, klass=None, mayCreate=True, mayExist=True, verifyAttributes=False, initfunction=None, **arguments):
    """Returns the object with given identifier in the given namespace. 
    Verifies that it is of the correct class. If no object is found, creates a new object of the given class
    Two initialization functions are called while remaining in thread-safe mode:
    - regular __init__(identifier, namespace, **arguments)
    - initfunction(newobject, **arguments)
    initfunction can be a method inside a class, e.g. self.initfunction calls initfunction(self, newobject, **arguments)
    Additional named arguments (**arguments) are passed to both functions. Make sure they can accept that.
    This function is thread-safe."""
    ## NOTE: please replace this function with:
    ##    xmlobject = klass(identifier=identifier, namespace=namespace, **arguments)
    ## only if you use mayCreate, mayExist, initfunction or verifyattributes you should use this function.
    if namespace == None:
        namespace = GetDefaultNamespace()
    assert(isinstance(namespace, XMLNamespace))
    identifier = UTF8(identifier)
    if identifier not in namespace.elements:
        if not mayCreate:
            raise UndefinedNamespaceException("No object with identifier %s in namespace %s" % (identifier, namespace.getURI()))
        if klass == None:
            klass = RDFObject
        if not issubclass(klass, RDFObject):
            raise TypeError("GetCreateRDFObject: klass %s is not an %s subclass." % (klass, RDFObject))
        xmlobject = klass(identifier=identifier, namespace=namespace, **arguments)
        if initfunction != None:
            # note that initfunction can be a method (self.mymethod()) or a function (myfunction())
            initfunction(xmlobject, **arguments)
    elif not mayExist:
        raise DuplicateNamespaceException("An other %s object with identifier %s already exists in namespace %s" % (klass.__name__, identifier, namespace.getURI()))
    xmlobject = namespace.elements[identifier]
    assert xmlobject != None    # None is an intermediate state in RDFObject.__new__(), but should be resolved before it returns
    if klass and not isinstance(xmlobject,klass):
        raise UndefinedNamespaceException("Object %s in namespace %s is a %s, instead of a %s" % (identifier, namespace.getURI(), type(xmlobject).__name__, klass.__name__))
    if verifyAttributes:
        VerifyEqualAttributes(xmlobject, ignoreNone=False, **arguments)
    return xmlobject


def GetRDFObject(identifier, namespace=None, klass=None, mayCreate=False, mayExist=True, verifyAttributes=False, initfunction=None, **arguments):
    """Returns the object with given identifier in the given namespace. 
    Verifies that it is of the correct class. Raises an UndefinedNamespaceException
    if the object is not found, or of the wrong class."""
    # mayCreate, mayExist are ignored (they are specified as argument to prevent that they end up in **arguments)
    return GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=klass, mayCreate=False, mayExist=True, verifyAttributes=verifyAttributes, initfunction=initfunction, **arguments)


def CreateRDFObject(identifier, namespace=None, klass=None, mayCreate=True, mayExist=False, verifyAttributes=False, initfunction=None, **arguments):
    """Verifies that the existing object does not yet exist. 
    Creates a new object of the given class and calls __init__ with identifier, namespace, and **arguments as arguments.
    In addition, a , and calls the initializer code: initfunction(newobject, **arguments).
    This function is thread-safe."""
    # mayCreate, mayExist are ignored (they are specified as argument to prevent that they end up in **arguments)
    return GetCreateRDFObject(identifier=identifier, namespace=namespace, klass=klass, mayCreate=True, mayExist=False, verifyAttributes=verifyAttributes, initfunction=initfunction, **arguments)


def DeleteRDFObject(rdfobject):
    """Delete the given rdfobject from the global repository. Note that you are responsible yourself to make sure the given RDFObject is really not referenced anymore."""
    pass
    global rdfobjects
    klass = type(rdfobject)
    if klass in rdfobjects:
        if rdfobject in rdfobjects[klass]:
            rdfobjects[klass].remove(rdfobject)
    namespace = rdfobject.namespace
    identifier = rdfobject.identifier
    if namespace and identifier in namespace.elements:
        del namespace.elements[identifier]
    # print "reference count of %s is %d" % (rdfobject, sys.getrefcount(rdfobject))
    # TODO: use sys.getrefcount to give warning if reference count >= 2

def DeleteAllRDFObjects():
    """Delete all known RDF Objects. Similar to DeleteAllNamespaces(), which also removes all known namespaces."""
    # method 1:
    for rdfobject in GetAllRDFObjects():
        DeleteRDFObject(rdfobject)
    # method 2:
    global rdfobjects
    rdfobjects = {}
    for namespace in GetNamespaces():
        namespace.elements = {}


def GetAllRDFObjects(klass=RDFObject, exactclass=False, namespace=None):
    """Return a list of all RDF objects of the given class. 
    If exactclass is False (the default), including objects of a subclass
    If a namespace is provided, then we search only in that namespace."""
    if not namespace:
        global rdfobjects
        objectlist = []
        for rdfklass in GetRDFClasses():
            if (klass == rdfklass) or ((not exactclass) and issubclass(rdfklass, klass)):
                objectlist.extend(rdfobjects[rdfklass])
    else:
        objectlist = []
        for obj in namespace.getElements():
            if (obj.__class__ == klass) or ((not exactclass) and issubclass(obj.__class__, klass)):
                objectlist.append(obj)
    objectlist.sort(key=rdfObjectKey)
    return objectlist



def GetRDFClasses(sortkey=None):
    global rdfobjects
    classes = rdfobjects.keys()
    # alternative, use inspect.getclasstree to create a logical sort order.
    # classtree = inspect.getclasstree(classes, True)
    if sortkey: # classKey
        classes.sort(key=sortkey)
    return classes


def VerifyEqualAttributes(subject, ignoreNone=False, **attributes):
    """Verifies that the given attributes are present in the xmlobject, and have the same value"""
    for (attribute, value) in attributes.iteritems():
        if not hasattr(subject, attribute):
            raise pynt.ConsistencyException("%s does not have an attribute %s" % (str(subject), attribute))
        existingvalue = getattr(subject, attribute)
        # we even give an error if one of the values is None
        if ignoreNone and ((value == None) or (existingvalue == None)):
            continue
        elif value != existingvalue:
            raise pynt.ConsistencyException("The %s of %s is currently %s, but it later turns out to be %s" % (attribute, str(subject), existingvalue, value))


# sort keys

def rdfObjectKey(subject):
    return subject.namespace.uri+subject.identifier

def classKey(subject):
    return subject.__name__

def xmlnamespaceKey(subject):
    return subject.uri


def UTF8(value):
    """Covert the value to a UTF-8 encoded string. The input can be unicode, string, number or boolean"""
    if isinstance(value, types.StringType):
        # WARNING: We assume here that the string is UTF-8 encoded!
        return value
    elif isinstance(value, types.UnicodeType):
        return value.encode('utf-8')
    elif isinstance(value, types.BooleanType):
        return str(value)
    elif isinstance(value, types.IntType):
        return str(value)
    elif isinstance(value, types.LongType):
        return str(value)
    elif isinstance(value, types.FloatType):
        return str(value)
    else:
        raise TypeError("Can not convert %s '%s' to an UTF-8 string" % (type(value), str(value)))



# Makes sure there is only one namespace with the same URI.
# Singleton pattern: keep the list of namespaces in a single (global) list

xmlnamespaces = {}        # dict, sorted by URL


class XMLNamespace(object):
    prefix      = None  # string or None. single word, used as prefix in. MUST be unique
    uri         = '#'   # URI of the namespace. MUST be unique
    schemaurl   = None  # URL with RDFS defining the schema
    humanurl    = None  # URL with human readable explanation of the schema
    elements    = None  # list (set in __init__)
    metaschema  = False # True if it is a "well known" schema, which meaning is hardcoded in this script
    layerschema = False # True if it is a schema defining a technology, which must be read to be understand, and to be able to parse network descriptions
    networkschema = False # True is the schema describes (part of) a network
    
    def __init__(self,uri,prefix=None,schemaurl=None,humanurl=None,metaschema=False,layerschema=False,networkschema=False):
        global xmlnamespaces
        self.elements = {}
        self.setURI(uri)
        if prefix:
            self.setPrefix(prefix)
        if schemaurl:
            self.setSchemaURL(schemaurl)
        if humanurl:
            self.setHumanURL(humanurl)
        self.metaschema  = bool(metaschema)
        self.layerschema = bool(layerschema)
        self.networkschema = bool(networkschema)
        if self.metaschema:
            schematype = "schema"
        elif self.layerschema:
            schematype = "layer"
        elif self.networkschema:
            schematype = "network"
        else:
            schematype = "regular"
        xmlnamespaces[uri] = self
        logger = logging.getLogger("pynt.xmlns")
        logger.info("Created %s namespace %s" % (schematype,uri))
    
    def __str__(self): # normal program output (no "" around strings)
        return '<%s %s>' % (type(self).__name__, self.uri)
    
    def __repr__(self): # debugging output ("" around string to distinguish "2" from 2)
        return '<%s %s>' % (type(self).__name__, self.uri)
        # return '<%s instance %s at %x>' % (type(self).__name__, self.uri, id(self))
    
    def setURI(self,uri):
        # check if prefix already exists
        if uri != self.uri:
            try:
                GetNamespaceByURI(uri)
            except UndefinedNamespaceException:
                # good, it doesn't exist yet
                pass
            else: 
                raise DuplicateNamespaceException("A namespace with URI %s already exists" % uri)
        self.uri = uri
    
    def setSchemaURL(self,schemaurl):   self.schemaurl = schemaurl
    def setHumanURL(self,humanurl):     self.humanurl = humanurl
    def getURI(self):                   return self.uri
    def getURIdentifier(self):          return self.uri
    def getSchemaURL(self):             return self.schemaurl
    def getHumanURL(self):              return self.humanurl
    def getExtraHumanURL(self):     
        if self.uri == self.humanurl:
            return ''
        else:
            return self.humanurl
    
    def __getitem__(self, key):
        return (self.uri + key)
    
    def getElements(self):              return self.elements
    
    def setPrefix(self,prefix):
        # check if prefix already exists
        if prefix != self.prefix:
            try:
                otherns = GetNamespaceByPrefix(prefix)
            except UndefinedNamespaceException:
                # good, it doesn't exist yet
                pass
            else:
                raise DuplicateNamespaceException("Can't create namespace %s. Prefix %s is already in use by %s." % (self.uri, prefix, otherns.uri))
        self.prefix = prefix
    
    def getPrefix(self):
        if self.prefix == None:
            self.prefix = GetUniquePrefix(self.uri)
        return self.prefix


def GetUniquePrefix(uri="",prefix=""):
    if prefix == "":
        match = re.search(r'.*\b([\w\.\-]+)\W*', uri)
        if match:
            prefix = match.group(1)
        else:
            prefix = 'ns'
    counter = 0
    global threadlock
    threadlock.acquire()
    while True:
        if counter == 0:
            testprefix = prefix
        else:
            testprefix = prefix + str(counter)
        try:
            GetNamespaceByPrefix(testprefix)
        except UndefinedNamespaceException:
            break
        counter += 1
    threadlock.release()
    return testprefix

# TODO: deprecte GetCreate* and replace with override of __metaclass__(type), __call__(cls, *args, **kwargs) and __new__(klass, self,uri,prefix=None,schemaurl=None,humanurl=None,metaschema=False,layerschema=False,networkschema=False, *args, **kwargs) in class XMLNamespace

def GetCreateNamespace(uri,prefix=None,schemaurl=None,humanurl=None,metaschema=False,layerschema=False,networkschema=False):
    """create a new namespace with given parameters.
    If a namespace with the same URI exist, check if the properties are the 
    same. If not, raise an exception. Returns the namespace instance"""
    global xmlnamespaces
    uri = UTF8(uri)
    if uri in xmlnamespaces:
        VerifyEqualAttributes(xmlnamespaces[uri], ignoreNone=True, prefix=prefix, schemaurl=schemaurl)
        return xmlnamespaces[uri]
    # namespace doesn't exist.
    global threadlock
    threadlock.acquire()
    # check if it still doesn't exist (another thread may have created it in the last few miliseconds)
    if uri not in xmlnamespaces:
        # create a new object
        xmlnamespaces[uri] = XMLNamespace(uri,prefix=prefix,schemaurl=schemaurl,humanurl=humanurl,metaschema=metaschema,layerschema=layerschema,networkschema=networkschema)
    else:
        VerifyEqualAttributes(xmlnamespaces[uri], ignoreNone=True, prefix=prefix, schemaurl=schemaurl)
    threadlock.release()
    return xmlnamespaces[uri]


def DeleteNamespace(namespace):
    """Delete the given namespace, as well as all RDFObject elements in the namespace"""
    # TODO: Use namespace.delete()?
    # remember that namespace.__del__() is only called if the object reference count is zero, which is NOT true for "del namespace".
    for rdfobject in namespace.elements.values():
        DeleteRDFObject(rdfobject)
    assert(len(namespace.elements) == 0)
    global xmlnamespaces
    del xmlnamespaces[namespace.uri]


def DeleteAllNamespaces():
    """Delete all global namespace objects, and removes all elements in the namespaces"""
    global rdfobjects
    rdfobjects = {}
    global xmlnamespaces
    xmlnamespaces = {}


def GetNamespaceByURI(uri):
    """return the XMLNamespace with the given namespace URI, or raise an UndefinedNamespaceException"""
    global xmlnamespaces
    if uri in xmlnamespaces:
        return xmlnamespaces[uri]
    else:
        raise UndefinedNamespaceException("No namespace with URI %s" % uri)


def GetNamespaceByPrefix(prefix):
    """return the XMLNamespace with the given prefix, or raise an UndefinedNamespaceException"""
    global xmlnamespaces
    for xmlns in xmlnamespaces.values():
        # Do not call getPrefix(); that will give in infinite recursion
        if xmlns.prefix == prefix:
            return xmlns
    raise UndefinedNamespaceException("No namespace with prefix %s" % prefix)


def GetNamespaceBySchemaURL(schemaurl):
    """return the XMLNamespace whose schema can be downloaded at the given URL, or raise an UndefinedNamespaceException"""
    global xmlnamespaces
    for xmlns in xmlnamespaces.values():
        if xmlns.schemaurl == schemaurl:
            return xmlns
    raise UndefinedNamespaceException("No namespace with schema at URL %s" % schemaurl)


def NamespaceExists(namespace):
    try:
        GetNamespaceByURI(namespace)
    except UndefinedNamespaceException:
        return False
    else: 
        return True


def GetNamespaces():
    """return a list of namespace objects that are currently in use"""
    global xmlnamespaces
    # We return all, including namespaces with len(elements) == 0
    namespaces = xmlnamespaces.values()
    namespaces.sort(key=xmlnamespaceKey)
    return namespaces



def GetDefaultNamespace():
    return GetCreateNamespace("#", prefix="local")


def GetCreateWellKnownNamespace(prefix, uri=None):
    """Create a namespace by prefix, using a lookup table of well-known prefixes and uris"""
    if (prefix == "rdf"):
        namespace = GetCreateNamespace(prefix = "rdf",
            uri       = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            schemaurl = 'http://www.w3.org/1999/02/22-rdf-syntax-ns',
            humanurl  = 'http://www.w3.org/TR/rdf-schema/',
            metaschema = True)
    elif (prefix == "rdfs"):
        namespace = GetCreateNamespace(prefix = "rdfs",
            uri       = 'http://www.w3.org/2000/01/rdf-schema#',
            schemaurl = 'http://www.w3.org/2000/01/rdf-schema',
            humanurl  = 'http://www.w3.org/TR/rdf-schema/',
            metaschema = True)
    elif (prefix == "owl"):
        namespace = GetCreateNamespace(prefix = "owl",
            uri       = 'http://www.w3.org/2002/07/owl#',
            schemaurl = 'http://www.w3.org/2002/07/owl',
            humanurl  = 'http://www.w3.org/TR/owl-semantics/',
            metaschema = True)
    elif (prefix == "xsd"):
        namespace = GetCreateNamespace(prefix = "xsd",
            uri       = 'http://www.w3.org/2001/XMLSchema#',
            schemaurl = 'http://www.w3.org/TR/xmlschema-2/#schema', # XSD format, not RDF!
            humanurl  = 'http://www.w3.org/TR/xmlschema-2/',
            metaschema = True)
    elif (prefix == "vcard"):
        namespace = GetCreateNamespace(prefix = "vcard",
            uri       = 'http://www.w3.org/2001/vcard-rdf/3.0#',
            schemaurl = 'http://www.w3.org/2001/vcard-rdf/3.0',
            humanurl  = 'http://www.w3.org/TR/vcard-rdf',
            metaschema = True)
    elif (prefix == "geo"):
        namespace = GetCreateNamespace(prefix = "geo",
            uri       = 'http://www.w3.org/2003/01/geo/wgs84_pos#',
            schemaurl = 'http://www.w3.org/2003/01/geo/wgs84_pos',
            humanurl  = 'http://www.w3.org/2003/01/geo/',
            metaschema = True)
    elif (prefix == "vs"):
        namespace = GetCreateNamespace(prefix = "vs",
            uri       = 'http://www.w3.org/2003/06/sw-vocab-status/ns#',
            schemaurl = 'http://www.w3.org/2003/06/sw-vocab-status/ns.rdf',
            humanurl  = None,
            metaschema= True)
    elif (prefix == "nmwgt"):
        namespace = GetCreateNamespace(prefix = "nmwgt",
            uri       = 'http://ogf.org/schema/network/topology/ctrlPlane/20080828/',
            schemaurl = 'http://ogf.org/schema/network/topology/ctrlPlane/20080828/',
            humanurl = 'http://nmwg.internet2.edu/nm-schema-base.html',
            metaschema = True)
    # Very well known namespaces
    elif (prefix == "dc"):
        namespace = GetCreateNamespace(prefix = "dc",
            uri       = 'http://purl.org/dc/elements/1.1/',
            schemaurl = 'http://purl.org/dc/elements/1.1/',
            humanurl  = 'http://dublincore.org/documents/dcmi-terms/#H2',
            metaschema = True)
    elif (prefix == "dcterms"):
        namespace = GetCreateNamespace(prefix = "dcterms",
            uri       = 'http://purl.org/dc/terms/',
            schemaurl = 'http://purl.org/dc/terms/',
            humanurl  = 'http://dublincore.org/documents/dcmi-terms/#H3',
            metaschema = True)
    elif (prefix == "dctype"):
        namespace = GetCreateNamespace(prefix = "dctype",
            uri       = 'http://purl.org/dc/dcmitype/',
            schemaurl = 'http://purl.org/dc/dcmitype/',
            humanurl  = 'http://dublincore.org/documents/dcmi-terms/#H5',
            metaschema = True)
    # NDL namespaces
    elif (prefix == "ndl") or (prefix == "topology"):
        namespace = GetCreateNamespace(prefix = "ndl",
            uri       = 'http://www.science.uva.nl/research/sne/ndl#',
            schemaurl = 'http://www.science.uva.nl/research/sne/schema/topology.rdf',
            humanurl  = 'http://www.science.uva.nl/research/sne/ndl/?c=11-Topology-Schema',
            metaschema = True)
    elif (prefix == "layer"):
        namespace = GetCreateNamespace(prefix = "layer",
            uri       = 'http://www.science.uva.nl/research/sne/ndl/layer#',
            schemaurl = 'http://www.science.uva.nl/research/sne/schema/layer.rdf',
            humanurl  = 'http://www.science.uva.nl/research/sne/ndl/?c=12-Layer-Schema',
            metaschema = True)
    elif (prefix == "capability"):
        namespace = GetCreateNamespace(prefix = "capability",
            uri       = 'http://www.science.uva.nl/research/sne/ndl/capability#',
            schemaurl = 'http://www.science.uva.nl/research/sne/schema/capability.rdf',
            humanurl  = 'http://www.science.uva.nl/research/sne/ndl/?c=13-Capability-Schema',
            metaschema = True)
    elif (prefix == "domain"):
        namespace = GetCreateNamespace(prefix = "domain",
            uri       = 'http://www.science.uva.nl/research/sne/ndl/domain#',
            schemaurl = 'http://www.science.uva.nl/research/sne/schema/domain.rdf',
            humanurl  = 'http://www.science.uva.nl/research/sne/ndl/?c=14-Domain-Schema',
            metaschema = True)
    elif (prefix == "physical") or (prefix == "location"):
        namespace = GetCreateNamespace(prefix = "physical",
            uri       = 'http://www.science.uva.nl/research/sne/ndl/physical#',
            schemaurl = 'http://www.science.uva.nl/research/sne/schema/physical.rdf',
            humanurl  = 'http://www.science.uva.nl/research/sne/ndl/?c=15-Physical-Schema',
            metaschema = True)
    else:
        raise UndefinedNamespaceException("The 'well-known' namespace with prefix '%s' is unknown to me. For technology-specific namespaces, use pynt.technologies.GetCreateWellKnownNamespace() instead pynt.xmlns.GetCreateWellKnownNamespace()" % prefix)
    # seeAlso: http://ebiquity.umbc.edu/blogger/100-most-common-rdf-namespaces/
    # seeAlso: http://www.schemaweb.info/
    
    if (uri != None) and (namespace.uri != uri):
        raise UndefinedNamespaceException("The prefix %s is reserved for URI %s; you requested URI %s." % (prefix, namespace.uri, uri))
    return namespace

