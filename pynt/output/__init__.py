# -*- coding: utf-8 -*-
"""This module defines BaseInput, a base class to retrieve a device data, 
and BaseOutput, a base class to render device data. 
If the output is written to file, the operation is atomic, or nearly 
atomic (in case it can't be atomic due to permissions)
As a reminder: all internal strings, like identifier, are represented 
in UTF-8. See for example the codecs module for helper functions."""

# builtin modules
import sys
import types
import tempfile     # for creation of temporary files
import os
import os.path      # for scriptname()
import socket       # for hostname()
import time         # for curtime()
import math         # for humanReadable()
import logging
import shutil       # for CopyFile()
# local modules
import pynt.elements
import pynt.xmlns


class BaseOutput(object):
    """The baseclass for an output method. Any output method should inherit this class.
    An output instance should be created with an "outfile" as argument. If it is not given, 
    sys.stdout is assumed.
    This can also be set later using the setOutputFile(outfile) function.
    
    The main function is BaseOutput.output which initiates the outputting process.
    The following methods are important:
        The output function does the following:
        1) setup logging (from pynt.output)
        2) Opens the file (self.openfile())
        3) Prints a header (self.printHeader())
        4) Prints the documents metadata (self.printDocumentMetaData())
        5) If no argument is given, it is set to be all network elements.
        6) Calls self.printElement()
        7) Call self.printFooter()
    
    The printElement function digs through the argument given to it.
    If a list or namespace is given, it calls printElement on each item consecutively.
    For other types of elements, print<Element> is called.
    
    Typical output methods should implement:
    printHeader, printDocumentMetaData, print<Element>, printFooter()
    """
    outfile         = None  # File object, open for write access
    subject         = None  # object to output
    atomic          = True  # if true, writes to temporary file first, making the file overwrite an atomic operation
    filename        = ""    # path of destination filename
    tempfile        = ""    # path of temporary filename
    metadata        = None  # dict with metadata strings
    
    def __init__(self, outfile=None, subject=None, atomic=True):
        self.logger = logging.getLogger("pynt.output")
        self.logger.debug("Created %s output" % (type(self).__name__))
        self.atomic = atomic
        self.metadata = {}
        self.setOutputFile(outfile)
        if subject:
            self.setSubject(subject)
        else:
            self.setSubject(pynt.xmlns.GetNamespaces())
    
    def __del__(self):
        if self.atomic and self.tempfile:
            os.remove(self.tempfile)
    
    def setOutputFile(self, outfile):
        if (outfile == self.outfile) or (outfile == self.filename):
            return
        if self.outfile:
            self.closefile()
        if outfile == None or outfile == sys.stdout:
            self.outfile = sys.stdout
        elif isinstance(outfile, types.FileType):
            self.outfile = outfile
        elif isinstance(outfile, types.StringTypes):
            self.filename = outfile
            self.openfile(append=False)
        else:
            raise AttributeError("output parameter for BaseOutput.setOutput() must be a FileType or filename. Got %s" % outfile)
            self.outfile = sys.stdout
        # assert(isinstance(self.outfile, types.FileType))
    
    def setSubject(self, subject):
        self.subject = subject
    
    def openfile(self, append=False):
        """Make sure self.outfile is a valid and open FileType"""
        
        if isinstance(self.outfile, types.FileType) and not self.outfile.closed:
            # file is already open
            self.logger.debug("Not opening file %s: it is already open" % self.filename)
            return
        if self.atomic:
            # I don't use tempfile.TemporaryFile() since the returned object is not an instanceof(types.FileType)
            (fd, self.tempfile) = tempfile.mkstemp()
            # Note: appending doesn't work, since we have a new tempfile by now (the old one is deleted)
            self.outfile = os.fdopen(fd, 'w+b')
            self.logger.debug("Opened %s for writing" % (self.tempfile))
        else:
            if append:
                self.outfile = file(self.filename, 'a+b')
            else:
                self.outfile = file(self.filename, 'w+b')
            
            self.logger.debug("Opened %s for writing" % (self.filename))
    
    def closefile(self):
        if self.outfile == None:
            return
        if self.atomic:
            if self.tempfile:
                self.outfile.close()
                MoveFile(self.tempfile, self.filename)
                self.tempfile = ""
        elif self.filename:
            self.outfile.close()
        self.outfile = None
    
    def output(self, subject=None):
        """output makes sure the file object is open, and calls an appropriate print* function. This is the main function"""
        
        if subject == None:
            self.logger.log(25, "Writing %s to %s" % (type(self).__name__, self.filename))
        else:
            self.logger.log(25, "Writing %s of %s to %s" % (type(self).__name__, subject, self.filename))
        if subject == None:
            subject = pynt.xmlns.GetNamespaces()
        if not self.outfile:
            self.openfile()
        self.printHeader()
        self.printDocumentMetaData(subject)
        self.printElement(subject)
        self.printFooter()
        self.closefile()
    
    def printElement(self, subject):
        # Function that recursively digs through anyhting that is thrown at it and prints it.
        if   isinstance(subject, pynt.elements.Device):              self.printDevice(subject)
        elif isinstance(subject, pynt.elements.ConnectionPoint):     self.printInterface(subject)
        # elif isinstance(subject, pynt.elements.PotentialMuxInterface): self.printPotentialMuxInterface(subject)
        elif isinstance(subject, pynt.elements.BroadcastSegment):    self.printBroadcastSegment(subject)
        elif isinstance(subject, pynt.elements.SwitchMatrix):        self.printSwitchMatrix(subject)
        elif isinstance(subject, pynt.elements.Location):            self.printLocation(subject)
        elif isinstance(subject, pynt.elements.AdminDomain):         self.printAdminDomain(subject)
        elif isinstance(subject, str):                               self.write(subject)
        elif isinstance(subject, pynt.layers.Property):              pass
        elif isinstance(subject, pynt.layers.AdaptationFunction):    pass
        elif isinstance(subject, pynt.layers.LabelSet):              pass
        elif isinstance(subject, pynt.layers.Layer):                 pass
        elif isinstance(subject, pynt.layers.ResourceClass):         pass
        elif isinstance(subject, pynt.layers.Resource):              pass
        elif isinstance(subject, pynt.xmlns.XMLNamespace):
            for el in subject.getElements().values():
                self.printElement(el)
        elif isinstance(subject, list):
            for el in subject:
                self.printElement(el)
        # FIXME: this is for testing, should be removed afterwards.
        #elif isinstance(subject, pynt.layers.Property): pass
        #elif isinstance(subject, pynt.layers.Resource): pass
        #elif isinstance(subject, pynt.layers.Layer):    pass
        #elif isinstance(subject, pynt.layers.AdaptationFunction): pass
        #elif isinstance(subject, pynt.layers.LabelSet): pass
        #elif isinstance(subject, pynt.layers.ResourceClass): pass
        #elif isinstance(subject, pynt.layers.ClassURI): pass
        else:
            self.printSubject(subject)
            raise AttributeError("Don't know how to output an object of type %s" % (type(subject)))
    
    def write(self,string):
        self.outfile.write(str(string)+"\n");
    
    def setMetaData(self, name, value):
        self.metadata[name] = value
    
    def printHeader(self):
        """Print header lines."""
        pass
    
    def printDocumentMetaData(self, subject):
        """Print the documents' metadata."""
        pass
    
    def printFooter(self):
        """Print footer lines."""
        pass
        
    def printSubject(self, subject):
        """subfunction of output. Assumes that the fileobject is open. Do not call directly, but use output()"""
        self.write(type(subject).__name__+":")
        self.write(str(subject))
    
    def printDevice(self, device):
        """subfunction of output. Assumes that the fileobject is open. Do not call directly, but use output()"""
        self.write(type(device).__name__+":")
        self.write(str(device))
    
    def printInterface(self, interface):
        """subfunction of output. Assumes that the fileobject is open. Do not call directly, but use output()"""
        self.write(type(interface).__name__+":")
        self.write(str(interface))

    def printBroadcastSegment(self, bc):
        """subfunction of output. Assumes that the fileobject is open. Do not call directly, but use output()"""
        self.write(type(bc).__name__+":")
        self.write(str(bc))

    def printLocation(self, loc):
        """subfunction of output. Assumes that the fileobject is open. Do not call directly, but use output()"""
        self.write(type(loc).__name__+":")
        self.write(str(loc))
    
    def printAdminDomain(self, dom):
        """subfunction of output. Assumes that the fileobject is open. Do not call directly, but use output()"""
        self.write(type(dom).__name__+":")
        self.write(str(dom))

    def printSwitchMatrix(self, switchmatrix):
        pass #TODO



def scriptname():
    try:
        scriptname = sys.argv[0]
    except IndexError:
        scriptname = ""
    if scriptname in ["-c", "", None]:
        scriptname = "python script"
    else:
        scriptname = os.path.basename(scriptname)
    return scriptname

def curtime():
    # e.g. "2007-02-01T17:19:43+01:00"
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')

def boolstr(string, true="True", false="False"):
    # ['0', 'false', 'down', 'unpowered', 'inactive', 'no', 'offline', 'unconfigured']:
    if str(string).lower()[0:2] in ['0', 'fa', 'do', 'un', 'in', 'no', 'of']:
        return false
    else:
        return true

def humanReadable(size, unit="", precision=2, binary=False):
    if binary:
        quantities = ['', 'ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Yi', 'Zi'] # the kibi, mebi, gibi, etc. units
        base = 1024
    else:
        quantities = ['', 'k', 'M', 'G', 'T', 'P', 'Y', 'Z'] # the kilo, mega, giga, etc. units
        base = 1000
    # unitjump = 1-math.pow(10,-(precision+1))/2
    unitjump = 1.25         # don't jump from 999 to 1.00k, but from 1249 to 1.25k
    formjump = unitjump     # 0.9995 or 1.9995 are typical (unitjump or 1+unitjump).
    unitmagnitude = int(math.floor(math.log(size/unitjump, base)))
    formmagnitude = int(math.floor(math.log(size/formjump, base)*3))
    unitmagnitude = min(unitmagnitude, len(quantities))
    formmagnitude = max(0,precision+3*unitmagnitude-formmagnitude)
    if (size < base) and isinstance(size, int):
        format = '%d %s%s'
    else:
        format = '%%3.%df %%s%%s' % (formmagnitude)
    size = size / math.pow(base, unitmagnitude)
    return format % (size, quantities[unitmagnitude], unit)

def MoveFile(source, destination):
    """move file from source to destination. Both are paths pointing to a file.
    This is an atomic operation, and does not change permissions of the file.
    Deletes source"""
    assert(len(source) > 0)
    assert(len(destination) > 0)
    # Check if we can use the atomic "rename" function: 
    logger = logging.getLogger("pynt.output")
    canuserename = True
    if os.path.exists(destination):
        # file already exists
        # check if the permission of the two files are the same
        srcstat = os.stat(source)
        dststat = os.stat(destination)
        try:
            if srcstat.st_mode != dststat.st_mode:
                os.chmod(source, dststat.st_mode)
            if srcstat.st_uid != dststat.st_uid:
                os.chown(source, dststat.st_uid, -1)
            if srcstat.st_gid != dststat.st_gid:
                os.chown(source, -1, dststat.st_gid)
        except OSError:
            canuserename = False
    if canuserename:
        # if so, do a move in the finder
        logger.debug("Doing an atomic rename from %s to %s" % (source, destination))
        try:
            # os.rename(source, destination)
            # we use shutil.move instead of os.rename, since os.rename() can handle moving between two file systems
            shutil.move(source, destination)
        except OSError:
            logger.debug("Caught OSError while renaming %s to %s" % (source, destination))
            canuserename = False
    if not canuserename:
        # read contents from file
        
        logger.debug("Doing a non-atomic rename from %s to %s" % (source, destination))
        infile = file(source, 'r+b')
        contents = infile.read()
        infile.close()
        outfile = file(destination, 'w+b')
        outfile.write(contents)
        outfile.close()
    try:
        os.remove(source)
    except OSError:
        pass
        # self.logger.debug("Could not delete temporary file %s" % (source))


def CopyFile(source, destination):
    """move file from source to destination. Both are paths pointing to a file.
    This is an atomic operation, and does not change permissions of the file.
    Deletes source"""
    shutil.copyfile(source,destination)

