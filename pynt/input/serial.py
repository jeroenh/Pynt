# -*- coding: utf-8 -*-
"""SerialInput -- Serialized input using pickle. This class will load all global data (all RDFObjects) as well as a pointer to a specific device."""

# builtin modules
import pickle
import logging
# local modules
import pynt.xmlns
import pynt.input


class SerialInput(pynt.input.BaseFetcher):
    """Serialized output using pickle"""
    filename    = None
    io          = None
    
    def setSource(self, source):
        self.setSourceFile(filename)
    
    def setSourceFile(self, filename, hostname=None):
        self.filename = filename
    
    def open(self):
        if not self.filename:
            raise RuntimeError("Call setSourceFile() before calling getSubject() or fetch() of a SerialInputFetcher instance")
        self.io = file(self.filename)
    
    def close(self):
        self.io.close()
    
    def retrieve(self):
        if len(pynt.xmlns.rdfobjects) > 0:
            raise RuntimeWarning("pynt.xmlns.rdfobjects is non-empty. Overwriting old information.")
        if len(pynt.xmlns.xmlnamespaces) > 0:
            raise RuntimeWarning("pynt.xmlns.xmlnamespaces is non-empty. Overwriting old information.")
        data = pickle.load(self.io)
        pynt.xmlns.rdfobjects    = data['rdfobjects']
        pynt.xmlns.xmlnamespaces = data['namespaces']
        self.subject                = data['subject']
