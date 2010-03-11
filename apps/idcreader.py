#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import optparse
import pynt.input.idc
import logging

# import pynt.technologies.ethernet
import pynt.output.debug
import pynt.output.manualrdf
import pynt.output.dot
import pynt.output.idc

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
    
    # pynt.logger.SetLogLevel(options.verbosity)
    pynt.logger.SetLogLevel(2)
    logger = logging.getLogger()
    # errorlog = pynt.logger.Logger(os.path.join(options.outputdir, "idc-error.log", verbosity=options.verbosity)
    
    filename = options.inputfilename

    # Input stuff
    fetcher = fetcherclass(filename)
    subject = fetcher.getNamespace()
    
    # Output stuff
    # if options.debug:
    #     out = pynt.output.debug.DebugOutput(os.path.join(options.outputdir, "idc-debug.txt"))
    #     out.output() 
    # 
    out = pynt.output.manualrdf.RDFOutput( os.path.join(options.outputdir, "idc-config.rdf"))
    out.output(subject)
    # 
    out = pynt.output.dot.DeviceGraphOutput(os.path.join(options.outputdir,"idc.dot"))
    out.output(subject)
    
    myout = pynt.output.dot.InterfaceGraphOutput(os.path.join(options.outputdir,'idc.interfaces.dot'))
    myout.output(subject)

    myout = pynt.output.idc.IDCTopoOutput(os.path.join(options.outputdir,'idc.xml'))
    myout.output(subject)
        

    # except:  # *any* kind of exception, including user-interupts, etc.
    #     # the write functions are atomic, so those will be fine when an exception occurs
    #     errorlog.logException()
    #     (exceptionclass, exception, traceback) = sys.exc_info()
    #     logger.exception("")
        
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
    parser.add_option("-d", "--debug", dest="debug", action="store_true",
                      help="Enable debug log output", default=False)
    parser.add_option("-o", "--output", dest="outputdir", action="store", type="string", metavar="PATH", 
                      help="The directory to store the output files", default=outputdir)
    parser.add_option("-q", "--quiet", dest="quietness", action="count", default=0, 
                      help="Quiet output (multiple -q makes it even more silent)")
    parser.add_option("-v", "--verbose", dest="verbosity", action="count", default=0, 
                      help="Verbose output (multiple -v makes it even chattier)")
    parser.add_option("-f","--file", dest="inputfilename", action="store", type="string",
                      help="Filename to read the IDC data from.", default=None)
    (options, args) = parser.parse_args(args=argv[1:])
    options.verbosity -= options.quietness
    return (options, args)



if __name__ == '__main__':
    Main(
            fetcherclass=pynt.input.idc.IdcReader, 
            argv=sys.argv
        )
