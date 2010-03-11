# -*- coding: utf-8 -*-
"""This package defines BaseFetcher, a base class to convert data to 
native RDFObjects. The Fetcher class is geared towards using the 
BaseInput class in pynt.protocols, but it can be completely different classes.
As a reminder: all internal strings, like identifier, should be 
represented in UTF-8. Use pynt.xmlns.UTF8 if you need help converting"""

# builtin modules
import logging
# local modules
import pynt.elements
import pynt.xmlns
import pynt.protocols.base
import threading
import pynt.logger

class ParsingException(Exception):
    "Raised when the input data has an unknown format"
    pass


# Global list of sources already fetched
# (For now, this is restricted to a list of URIs)
visitedsources = []

def AlreadyFetched(source):
    """Returns True if the given URI is already fetched"""
    global visitedsources
    return source in visitedsources


# TODO: add lock to make sure there is only one fetcher per source.
# Lock is required if two threads create a source at the same time.
# pynt/input/rdf.py/GetCreateRDFFetcher has this routine, and should me moved here.

class BaseFetcher(object):
    """Abstract class. Create an object, log in to a hostname (or filename or URL) and return a device object, 
    or otherwise sets RDF Objects"""
    threadsafe  = False # Should locking be used?
    lock        = None  # Locking object for this class
    subject     = None  # subject object to fetch
    subjectClass = pynt.elements.Device
    
    def __init__(self, source):
        #def __init__(self, identifier, nsuri="#", io=None, threadsafe=False):
        # self.identifier = identifier
        # self.nsuri      = nsuri
        # if self.nsuri:
        #     self.namespace  = pynt.xmlns.GetCreateNamespace(self.nsuri)
        # else:
        #     self.namespace  = None
        # if io:
        #     assert(isinstance(io, pynt.protocols.base.BaseInput))
        #     self.io = io
        pynt.logger.InitLogger(50)
        self.logger = logging.getLogger("pynt.input")
        self.logger.debug("Created %s input" % (type(self).__name__))
        
        if self.threadsafe:
            self.lock = threading.Lock()
            self.logger.debug("Created class fetcher lock object %s" % self.lock)
        
        ###assert(source != None)
        self.setSource(source)
    
    def getSource(self):
        raise NotImplementedError("Fetcher class %s must override getSource() function" % type(self).__name__)
    
    def setSource(self, source):
        raise NotImplementedError("Fetcher class %s does not know how to retrieve data from source %s" % (type(self).__name__, source))
    
    def setSourceHost(self, hostname, port=None):
        raise NotImplementedError("Fetcher class %s does not know how to retrieve data from a host" % type(self).__name__)
        # self.setSource(hostname=hostname, port=port)
    
    def setSourceURL(self, url):
        raise NotImplementedError("Fetcher class %s does not know how to retrieve data from a URL" % type(self).__name__)
        # self.setSource(url=url)
    
    def setSourceFile(self, filename, hostname=None):
        raise NotImplementedError("Fetcher class %s does not know how to retrieve data from file" % type(self).__name__)
        # self.setSource(hostname=hostname, port=port)
    
    def subjectFactory(self):
        """Create a new Device object using a preset-default type. Raises an exception if it already existed"""
        self.logger.debug("Creating an RDFObject of class %s" % self.subjectClass)
        assert(issubclass(self.subjectClass, pynt.xmlns.RDFObject))
        #return self.subjectClass(identifier=self.identifier, namespace=self.namespace)
        return pynt.xmlns.GetCreateRDFObject(identifier=self.identifier, namespace=self.namespace, klass=self.subjectClass)
    
    def getSubject(self):
        if self.subject == None:
            self.subject = self.subjectFactory()
            self.fetch()
        return self.subject
    
    def open(self):
        pass
    
    def close(self):
        pass
    
    def fetch(self):
        """login, retrieve and disconnect"""
        try:
            if self.threadsafe: # First acquire the thread lock
                self.lock.acquire()
            success = False
            logger = logging.getLogger("pynt.input")
            self.open()
            
            logger.debug("Parsing information using %s input" % (type(self).__name__))
            self.retrieve()
            
            # We only record the fetching *after* storing all info in RDFobjects.
            # So AlreadyFetched() only returns True if all information is stored.
            global visitedsources
            visitedsources.append(self.getSource())
            
            success = True
        finally:
            if self.threadsafe: # First release the thread lock
                self.lock.release()
            
            # if success is still False, an exception was raised. close, 
            # and raise original, even if close gives a new exception.
            if success:
                self.close()
            else:
                logger.debug("Caught exception; Closing connection before reporting the error.")
                try:
                    self.close()
                except Exception:  # any exception except keyboard interrupts and system errors
                    pass # ignore later exceptions
    
    def retrieve(self):
        pass
    

class BaseDeviceFetcher(BaseFetcher):
    identifier  = ""
    nsuri       = ""    # namespace URI string
    io          = None  # instance of Input class (subClassOf BaseInput)
    
    def __init__(self, source, identifier, nsuri="#", io=None):
        BaseFetcher.__init__(self, source)
        self.identifier = identifier
        self.nsuri      = nsuri
        if self.nsuri:
            self.namespace  = pynt.xmlns.GetCreateNamespace(self.nsuri)
        else:
            self.namespace  = None
        if io:
            assert(isinstance(io, pynt.protocols.base.BaseInput))
            self.io = io
    
    def getSource(self):
        return self.hostname
    
    def setSource(self, source):
        self.hostname = source
        self.setSourceHost(source)
    
    def open(self):
        if not self.io:
            raise RuntimeError("Call setSourceHost() or setSourceFile() before calling getSubject() or fetch() of a Fetcher instance")
        self.io.start()
    
    def close(self):
        self.io.stop()
    
    def getDevice(self):
        subject = self.getSubject()
        assert(isinstance(subject, pynt.elements.Device))
        return subject
    


class BaseRecursiveFetcher(BaseFetcher):
    """The BaseRecursiveFetcher takes a 3-step approach to recursively 
       fetching all sources:
       (1) Prepare the recursion by looking for all sources to fetch 
           that are linked in the current source
       (2) Recursively fetch the sources
       (3) Fetch the information from its own source

       The first step is an abstract definition, subclasses should 
       implement this.

       In the second step, a new fetcher class will be created for 
       every source. If dependencies are involved, it is the task
       of the function implementation in (1) to make sure these
       sources are put in the list in the correct fetching order.
       
       Fetching is implemented depth-first. The first source will
       be branched and fetched until all recursions in that source
       have been fetched, or until the max. recursion depth has 
       been reached for that branch."""
           
    sourcequeue = None  # list of sources yet to visit
    recursiondepth = 0  # recursion depth for 
    maxrecursiondepth = 10
    sourcehierarchy = None # parent sources, who have been calling this fetcher in fetchSource(). Used to detect loops.
    
    def __init__(self, source):
        BaseFetcher.__init__(self, source)
        self.sourcehierarchy = [source]
        self.sourcelist = []    # list of sources, with fetcher class
    
    def buildSourceQueue(self):
        """This is an abstract function and should be implemented by a real
           fetcher class."""
        pass
    
    def fetchSource(self, source, fetcherclass=None):
        """Fetch a related source before proceeding with the currect source.
        If fetcher is not defined, clone the current class"""
        if fetcherclass == None:
            fetcherclass = self.__class__
        logger = logging.getLogger("pynt.input")
        # Check recursion depth
        if self.recursiondepth >= self.maxrecursiondepth:
            logger.warning("Maximum recursion depth %d reached for source %s") % (self.maxrecursiondepth, source)
            return False
        if source in self.sourcehierarchy:
            # source 1 fetches other source 2, which fetches source 3, which fetches source 1
            logger.info("Loop prevention of source %s: %s" % (source,self.sourcehierarchy[self.sourcehierarchy.index(self.sourcehierarchy[-1]):]))
            return False
        if AlreadyFetched(source):
            logger.info("Skip source %s: it has already been fetched" % source)
            return False
        # create new fetcher
        assert(issubclass(fetcherclass, BaseRecursiveFetcher))
        fetcher = fetcherclass(source)
        # set recursion depth
        fetcher.recursiondepth = self.recursiondepth + 1
        fetcher.maxrecursiondepth = self.maxrecursiondepth
        # set source parent hierarchy
        fetcher.sourcehierarchy = self.sourcehierarchy + fetcher.sourcehierarchy
        # and -finally- fetch
        fetcher.fetch()
        return True
    
    def sourceInList(self, findsource):
        """Test if a certain source is already in our current sourcelist, or
           if the source is the same as our own source."""
        if str(self.url) == str(findsource):
            return True
        for (source, fetcherclass) in self.sourcelist:
            if str(source) == str(findsource):
                return True
        return False

    def queueSource(self, source, fetcherclass=None, prepend=False):
        """Add a related source to a (seeAlso) queue. The given URL will be fetched after the current
        fetcher is finished."""
        if fetcherclass == None:
            fetcherclass = self.__class__
        logger = logging.getLogger("pynt.input")

        if self.sourceInList(source):
            pass
            # This statement will generate a lot of clutter 
            #logger.debug("This source is already in the sourcelist of source %s" % self.url)
        elif prepend:
            self.sourcelist.insert(0, (source, fetcherclass))
            logger.debug("Prepended source %s found in source %s" % (source, self.url))
        else:
            self.sourcelist.append((source, fetcherclass))
            logger.debug("Appended source %s found in source %s" % (source, self.url))

    def fetchQueuedSources(self):
        """Fetch sources added to the queue using queueSource()."""
        # logger.logsomething() ## TODO
        for (source, fetcherclass) in self.sourcelist:
            self.fetchSource(source, fetcherclass)
    
    def attachSource(self, source, subject):
        """Add a related (seeAlso) source to a subject. The given URL will NOT be fetched automatically.
        Instead, it will be added to an object."""
        logger = logging.getLogger("pynt.input")
        logger.info("Add source %s to %s" % (source, subject))
        subject.attachSource(source)
    
    def fetch(self):
        """Here the three steps in the fetching process are called:
           (1) Prepare sources queue for this source
           (2) Recursively fetch queued sources in order
           (3) Fetch own source"""

        # First prepare the source queue
        # TODO: because we will be parsing a source into the graph, we should 
        # implement thread safety somewhere. Maybe implement a function 
        # similar to BaseFetcher.fetch() in that class for this purpose?
        self.buildSourceQueue()

        # Then fetch these queued sources
        self.fetchQueuedSources()
        
        # And lastly, fetch our own source
        BaseFetcher.fetch(self)
