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
import pynt.algorithm
import pynt.algorithm.output


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
    
    identifier = "networkreader"
    errorfile  = os.path.join(options.outputdir, "%s-error.log"      % identifier)  # log of errors
    debugfile  = os.path.join(options.outputdir, "%s-debug.txt"      % identifier)  # human readable memory dump
    errorlog = pynt.logger.Logger(errorfile, verbosity=options.verbosity)
    
    try:
        #fetcher = pynt.input.rdf.GetCreateRDFFetcher(fetcherclass, url)
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

    # Do the pathwalk 
    pw = pynt.algorithm.PathWalk()
    # Retrieve connection point http://rembrandt0.uva.netherlight.nl#Rembrandt0:eth2
    (namespace, identifier) = pynt.xmlns.splitURI('http://speculaas.uva.netherlight.nl#intf51')
    startif = pynt.elements.GetCreateInterface(identifier, namespace)
    print identifier, namespace
    print startif.getName()
    # Retrieve connection point http://rembrandt7.uva.netherlight.nl#Rembrandt7:eth2
    (namespace, identifier) = pynt.xmlns.splitURI('http://speculaas.uva.netherlight.nl#intf11')
    endif = pynt.elements.GetCreateInterface(identifier, namespace)
    print identifier, namespace
    print endif.getName()

    logger.setLevel(logging.DEBUG)
    
    pw.setEndpoints(startif, endif)
    pw.setPrinter(pynt.algorithm.output.TextProgressPrinter())

    solutions = pw.findShortestPath()

    namespaces = []
    for solution in solutions:
        for hop in solution:
            namespaces.append(hop.cp.getNamespace())

    output = pynt.output.dot.InterfaceGraphOutput('foo.dot')
    dotprinter = pynt.algorithm.output.SingleFilePrinter(output, namespaces)
    pw.addPrinter(dotprinter)

    pw.printSolution()

if __name__=="__main__":
    # pynt.input.commandline.DeviceMain parses the sys.arg; the given values are the compulsory default values
    Main(
            fetcherclass=pynt.input.rdf.RDFSchemaFetcher, 
            url=os.path.join(pynt.input.commandline.GetDefaultNetworkExamplesDir(),'uvalight.rdf')
        )

