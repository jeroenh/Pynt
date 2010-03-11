#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""logger module: adds handler to the logger starting with 'network'. It will write this to file.
This module is not intended to be an interface to the logging module. Just keep using that one."""

# builtin modules
import logging
import types
import sys
# local modules
# None

# Modify logging:


def InitLogger(loglevel=40):
    # loglevel default is ERROR, it is increased for each verbosity, and decreased for quietness
    logging.basicConfig(level=loglevel, stream=sys.stderr, format='%(levelname)-8s %(name)-15s %(message)s')
    # Adding "Notice" loglevel
    # Note that we MUST set logging/basicConfig before logging.addLevelName, or else basicConfig() is ignored
    # (don't ask me why)
    # This leads to a terrible chicken & egg problem: simply importing technology modules already
    # creates XMLNamespace objects, which logs with NOTICE level. However, this statement is only 
    # executed later. And in fact, can't be executed before, as it has to be called after
    # logging.basicConfig. The fix is to hard-code 25 as the log level for NOTICE in the scripts.
    # TODO: we may want to fix it an other way, so we see the logging of the XMLNamespace calls.
    if not hasattr(logging, "NOTICE"):
        assert((logging.WARNING+logging.INFO)/2 == 25) # We can't use logging.NOTICE elsewhere
        logging.debug("Creating log level notice")
        logging.addLevelName(25, "NOTICE")


def SetLogLevel(verbosity=0):
    loglevel = VerbosityToLogLevel(verbosity)
    logger = logging.getLogger()
    if len(logger.handlers) == 0:
        # Logging is not yet configured. Configure it.
        InitLogger(loglevel)
    else:
        logger.setLevel(loglevel)

def GetLogger(name):
    logger = logging.getLogger()
    if len(logger.handlers) == 0:
        # Logging is not yet configured. Configure it.
        InitLogger()
    return logging.getLogger(name)

def VerbosityToLogLevel(verbosity):
    # loglevel default is ERROR, it is increased for each verbosity, and decreased for quietness
    # verbosity loglevel
    # -3        50  logging.CRITICAL
    # -2        40  logging.ERROR
    # -1        30  logging.WARNING 
    #  0        25  logging.NOTICE
    # +1        20  logging.INFO
    # +2        10  logging.DEBUG
    if verbosity == 0:
        loglevel = 40
    elif verbosity > 0:
        loglevel = max(logging.CRITICAL - 10*verbosity, 1)
    else:
        loglevel = min(logging.WARNING - 10*verbosity, logging.CRITICAL)
    return loglevel


class CounterFilter(logging.Filter):
    count = 0
    loglevel = logging.ERROR
    def filter(self, record):
        if record.levelno >= self.loglevel:
            self.count += 1
        return 1  # don't actually filter; just count
    def setLevel(self,loglevel):
        self.loglevel = loglevel

class Logger(object):
    """File logger; logs all warnings and errors to file. 
    It overwrites the file instead of appending, but can 
    report the number or warnings/errors previously in the file."""
    outfile         = None  # File object, open for write access
    filename        = ""    # path of destination filename
    logger          = None  # logger object
    prevcount       = 0     # counter of lines in file before we overwrote it
    curcount        = 0     # counter of lines in file since start of logging
    countfilter     = None  # filter object
    loglevel        = logging.ERROR
    
    def __init__(self, outfile=None, verbosity=None):
        # TODO: There is an error in this file logger.
        # The loglevel of the logger("pynt") is determined by the verbosity.
        # If this is higher then the loglevel of the logfile handler, then the 
        # no log entries are written to the logfile with lower level.
        # So apparently, we have to adjust the loglevel of the logger as well
        # as the loglevel of the handler. However, that also means the loglevel 
        # of the regular output (to stderr) is affected, and we have to correct for that.
        # This is ugly, but I (Freek) don't see another way around it.
        if verbosity != None:
            self.loglevel = VerbosityToLogLevel(verbosity)
        self.loglevel = min(25, self.loglevel)   # we're logging WARNINGS too
        self.countfilter = CounterFilter()
        # self.countfilter.setLevel(logging.ERROR) # Only count errors, despite that we log more
        logger = self.getLogger()
        if outfile == None:
            outfile = sys.stderr
        # the part below should only be carried out when outfile != None
        else:
            self.readPrevLineCount(outfile)
            try:
                self.emptyFile(outfile)
            except IOError:
                logger.error("Can't open log file %s for writing" % outfile)
                return # stop here; don't add log handler after an IOError
        handler = self.getHandler(outfile)
        # TODO: WARNING: log entries are only registered if the loglevel of the logger AND the handler are high enough.
        # Currently, we only adjust the level of the handler....
        handler.setLevel(self.loglevel)
        handler.addFilter(self.countfilter)
        logger.addHandler(handler)
    
    def getLogger(self):
        return logging.getLogger("pynt")
    
    def getHandler(self, outfile):
        if isinstance(outfile, types.FileType):
            handler = logging.StreamHandler(outfile)
        elif isinstance(outfile, types.StringTypes):
            self.filename = outfile
            handler = logging.FileHandler(outfile)
        else:
            raise AttributeError("output parameter for Logger.setOutput() must be a FileType or filename")
        formatter = logging.Formatter('%(asctime)s\t%(name)s\t%(levelno)s\t%(message)s')
        handler.setFormatter(formatter)
        return handler
    
    def readPrevLineCount(self, outfile):
        if not isinstance(outfile, types.StringTypes):
            return
        try:
            infile = file(outfile, 'r+b')
            contents = infile.readlines()
            infile.close()
            self.prevcount = 0
            for logline in contents:
                logline = logline.split('\t', 4)
                if (len(logline) > 3) and logline[2].isdigit() and (int(logline[2]) >= self.loglevel) and logline[1].startswith("network"):
                    self.prevcount += 1
        except IOError:
            pass
    
    def emptyFile(self, outfile):
        infile = file(outfile, 'w+b')
        infile.write("")
        infile.close()
    
    def getPrevErrorCount(self):
        return self.prevcount
    
    def getCurErrorCount(self):
        return self.countfilter.count
    
    def logException(self, excinfo = None):
        if excinfo == None:
            excinfo = sys.exc_info()
        (exceptionclass, exception, traceback) = excinfo
        logger = self.getLogger()
        message = exceptionclass.__name__
        if hasattr(exception, 'args') and (len(exception.args) > 0):
            message = message + ": " + str(exception.args[0])
        logger.error(message)
        # logger.exception(exception.args[0])  # this will call sys_exc_info() itself and log the whole trace
    
