#!/usr/bin/env python
# -*- coding: utf-8 -*-

## TEMPORARY FILE, used for testing pynt.input.rdf module ##

# built-in modules
import sys
import logging
import optparse
import os.path
# local modules
try:
    import pynt
except ImportError:
    raise ImportError("Package pynt is not available. Copy pynt to python/site-packages, or set $PYTHONPATH\n")
import pynt.input
import pynt.input.commandline
import pynt.input.rdf
import pynt.input.serial
import pynt.logger
import pynt.output.debug


def Main(fetcherclass, url, argv=None):
    """
    main() function. Parse command line arguments, fetch information from a device, 
    parsing it into a memory structure (specified by pynt.elements) and 
    write that to files in multiple formats
    """
    (options, args) = pynt.input.commandline.GetOptions(argv)
    if len(args) > 0:
        # override url
        url = args[0]
    
    pynt.logger.SetLogLevel(options.verbosity)
    logger = logging.getLogger()
    
    if options.simulate:
        pynt.input.rdf.setWorkOnline(False)
    
    identifier = "devicereader"
    errorfile  = os.path.join(options.outputdir, "%s-error.log"      % identifier)  # log of errors
    debugfile  = os.path.join(options.outputdir, "%s-debug.txt"      % identifier)  # human readable memory dump
    errorlog = pynt.logger.Logger(errorfile, verbosity=options.verbosity)
    
    try:
        fetcher = fetcherclass(url)
        logger.debug("Reading from RDF")
        fetcher.fetch()  # fetches data from RDF schema
        #ethns = pynt.xmlns.GetCreateNamespace("http://www.science.uva.nl/research/sne/ndl/ethernet#")
        out = pynt.output.debug.DebugOutput(debugfile)
        out.output()
        
    except:  # *any* kind of exception, including user-interupts, etc.
        # the write functions are atomic, so those will be fine when an exception occurs
        errorlog.logException()
        (exceptionclass, exception, traceback) = sys.exc_info()
        logger.exception("")
    


if __name__=="__main__":
    # pynt.input.commandline.DeviceMain parses the sys.arg; the given values are the compulsory default values
    Main(
            fetcherclass=pynt.input.rdf.RDFDeviceFetcher, 
            url=os.path.join(pynt.input.commandline.GetDefaultOutputDir(),'beautycees-config.rdf')
        )

