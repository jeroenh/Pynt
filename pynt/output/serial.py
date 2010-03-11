# -*- coding: utf-8 -*-
"""SerialOutput -- Serialized output using pickle. This class will store all global data (all RDFObjects) as well as a pointer to a specific device."""

# builtin modules
import types
import pickle
import logging
import time
# local modules
import pynt.xmlns
import pynt.output



class SerialOutput(pynt.output.BaseOutput):
    """Serialized output using pickle"""
    def output(self, subject=None):
        # WARNING: you must make sure no file objects are still in the object.
        # In particular, set any closed network connections to None after disconnecting
        logger = logging.getLogger("pynt.output")
        if subject == None:
            logger.log(25, "Writing %s to %s" % (type(self).__name__, self.filename))
        else:
            logger.log(25, "Writing %s of %s to %s" % (type(self).__name__, subject, self.filename))
        self.openfile()
        data = {}
        data['time']       = time.time()
        data['rdfobjects'] = pynt.xmlns.rdfobjects
        data['namespaces'] = pynt.xmlns.xmlnamespaces
        data['subject']    = subject
        pickle.dump(data,self.outfile)
        self.closefile()


