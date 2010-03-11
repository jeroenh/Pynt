#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Test suite for ospf'''

# built-in modules
import sys
import os.path
import logging
import optparse
# local modules
try:
    import pynt
except ImportError:
    raise ImportError("Package pynt is not available. Copy pynt to python/site-packages, or set $PYTHONPATH\n")
import pynt.logger
import pynt.input.commandline
import pynt.input.ospf



def Main(fetcherclass, outputdir=None, argv=None):
    """
    main() function. Parse command line arguments, fetch information from a device, 
    parsing it into a memory structure (specified by pynt.elements) and 
    write that to files in multiple formats
    """
    (options, args) = GetOptions(argv)
    if len(args) > 0:
        # override hostname
        hostname = args[0]
    
    pynt.logger.SetLogLevel(options.verbosity)
    logger = logging.getLogger()
    if options.ip:
        hostname = options.ip
    else:
        hostname = "ospf"
    identifier = hostname.split(".")[0]
    errorfile  = os.path.join(options.outputdir, "%s-error.log"      % identifier)  # log of errors
    serialfile = os.path.join(options.outputdir, "%s-serial.pickle"  % identifier)  # memory dump
    debugfile  = os.path.join(options.outputdir, "%s-debug.txt"      % identifier)  # human readable memory dump
    ndl24file  = os.path.join(options.outputdir, "%s-config.rdf"     % identifier)  # All information in latest NDL
    staticfile = os.path.join(options.outputdir, "%s-interfaces.rdf" % identifier)  # Static interface configuration in NDL (no configuration info)
    ndl22file  = os.path.join(options.outputdir, "%s-v22.rdf"        % identifier)  # NDL v2.2 deprecated version with all info
    dotfile    = os.path.join(options.outputdir, "%s.dot"            % identifier)  # Dot output for generating a graph
    # iologfile  = options.iologfile                # file to log raw I/O communications with devices
    # passwdfile = options.configfile               # file with usernames and passwords
    errorlog = pynt.logger.Logger(errorfile, verbosity=options.verbosity)
    
    try:
        namespaceuri = "#"
        identifier   = hostname.split(".")[0].capitalize()
        fetcher = fetcherclass(hostname, nsuri=namespaceuri, identifier=identifier)
        if options.inputfilename:
            logger.log(25, "Performing simulated query on %s" % hostname)
            fetcher.setSourceFile(options.inputfilename, hostname=hostname) # hostname is used to set prompt
        elif options.ip:
            logger.log(25, "Performing live query on %s" % hostname)
            fetcher.setSourceHost(hostname, localport=options.localport, remoteport=options.remoteport)
        else:
            sys.exit("Please specify either an ip (-i) or a file (-f).")
        # fetches data from device and returns object structure.
        # The subject is something that can be passed on to BaseOutput.output();
        # Typically a Device object or namespace.
        subject = fetcher.getSubject()
        subject = subject.getNamespace()
        
        if options.ip:
            out = pynt.output.serial.SerialOutput(serialfile)
            out.output(subject)
        
        out = pynt.output.debug.DebugOutput(debugfile)
        out.output()
        
        out = pynt.output.manualrdf.RDFOutput(ndl24file)
        out.output(subject)
        
        out = pynt.output.dot.DeviceGraphOutput(dotfile)
        out.output(subject)
        

    except:  # *any* kind of exception, including user-interupts, etc.
        # the write functions are atomic, so those will be fine when an exception occurs
        errorlog.logException()
        (exceptionclass, exception, traceback) = sys.exc_info()
        logger.exception("")

def GetOptions(argv=None):
    """
    Parse command line arguments.
    """
    if argv is None:
        # allow user to override argv in interactive python interpreter
        argv = sys.argv
    # default is 'output/' if it exists, otherwise './'.
    if os.path.exists('output'):
        outputdir = 'output'
    elif os.path.exists(os.path.join(os.path.dirname(os.path.dirname(pynt.__file__)),'output')):
        outputdir = os.path.join(os.path.dirname(os.path.dirname(pynt.__file__)),'output')
    else:
        outputdir = '.'
    parser = optparse.OptionParser(conflict_handler="resolve")
    # standard option: -h and --help to display these options
    parser.add_option("--man", dest="man", action="store_true", default=False, 
                      help="Print extended help page (manual)")
    parser.add_option("-i", "--ip", dest="ip", action="store", type="string",
                      help="IP address to connect to.")
    parser.add_option("-o", "--output", dest="outputdir", action="store", type="string", metavar="PATH", 
                      help="The directory to store the output files", default=outputdir)
    parser.add_option("-p", "--port", dest="localport", action="store", type="int", 
                      help="The local port to listen to or connect to", default=4000)
    parser.add_option("-r", "--remote", dest="remoteport", action="store", type="int", 
                    help="The remote port to connect to", default=2607)        
    parser.add_option("-q", "--quiet", dest="quietness", action="count", default=0, 
                      help="Quiet output (multiple -q makes it even more silent)")
    parser.add_option("-v", "--verbose", dest="verbosity", action="count", default=0, 
                      help="Verbose output (multiple -v makes it even chattier)")
    parser.add_option("-f","--file", dest="inputfilename", action="store", type="string",
                      help="Filename to read the simulated data from.", default=None)
    (options, args) = parser.parse_args(args=argv[1:])
    options.verbosity -= options.quietness
    return (options, args)



if __name__ == '__main__':
    Main(
            fetcherclass=pynt.input.ospf.OspfFetcher, 
            argv=sys.argv
        )
    
