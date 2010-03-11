# -*- coding: utf-8 -*-
"""Helper functions for command line tools"""

# built-in modules
import logging
import sys
import optparse
import os.path
# local modules
import pynt
import pynt.elements
import pynt.xmlns
import pynt.input
# input/output modules
import pynt.input.serial
import pynt.output.serial
import pynt.output.debug
import pynt.output.manualrdf
import pynt.output.dot
import pynt.input.usernames

import pynt.logger


def GetDefaultDir(dir):
    # default is 'ndl/<dir>/' if it exists, otherwise './'.
    if os.path.exists(dir):
        return dir
    elif os.path.exists('../%s' % dir):  # and os.getcwd().endswith("apps")
        return '../%s' % dir
    elif os.path.exists(os.path.join(os.path.dirname(os.path.realpath(pynt.__file__)), '..', dir)):
        return os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(pynt.__file__)), '..', dir))
    else:
        return '.'

def GetDefaultOutputDir():
    return GetDefaultDir('output')
def GetDefaultNetworkExamplesDir():
    return GetDefaultDir('network-examples')


def GetOptions(argv=None):
    """
    Parse command line arguments.
    """
    if argv is None:
        # allow user to override argv in interactive python interpreter
        argv = sys.argv
    parser = optparse.OptionParser(conflict_handler="resolve")
    # standard option: -h and --help to display these options
    parser.add_option("--man", dest="man", action="store_true", default=False, 
                      help="Print extended help page (manual)")
    parser.add_option("-c", "--config", dest="configfile", action="store", metavar="FILE", 
                      help="Configuration file to read username and password", default="usernames.cfg")
    parser.add_option("-o", "--output", dest="outputdir", action="store", type="string", metavar="PATH", 
                      help="The directory to store the output files", default=GetDefaultOutputDir())
    parser.add_option("-l", "--iolog", dest="iologfile", action="store", type="string", metavar="PATH", 
                      help="The file to log raw device I/O communication", default=None)
    parser.add_option("-p", "--port", dest="port", action="store", type="int", 
                      help="The network port to listen to or connect to", default=None)
    parser.add_option("-u", "--username", dest="username", action="store", type="string", 
                      help="The username to log in to the device", default=None)
    parser.add_option("--password", dest="password", action="store", type="string", 
                      help="The password to log in to the device", default=None)
    parser.add_option("-q", "--quiet", dest="quietness", action="count", default=0, 
                      help="Quiet output (multiple -q makes it even more silent)")
    parser.add_option("-v", "--verbose", dest="verbosity", action="count", default=0, 
                      help="Verbose output (multiple -v makes it even chattier)")
    parser.add_option("-s", "--simulate", dest="simulate", action="store", default=None,
                      help="Read information not from device, but from file. Valid options are 'pickle', 'command' and 'offline'")
    parser.add_option("-f","--file", dest="inputfilename", action="store", type="string",
                      help="Filename to read the simulated data from.", default=None)
    parser.add_option("--nonames", dest="skipnames", action="store_true",
                      help="Do not read any configuration data about interface names from the Calient (very slow device)")
    (options, args) = parser.parse_args(args=argv[1:])
    options.verbosity -= options.quietness
    return (options, args)



def DeviceMain(fetcherclass, hostname, argv=None):
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
    
    identifier = hostname.split(".")[0]
    errorfile  = os.path.join(options.outputdir, "%s-error.log"      % identifier)  # log of errors
    serialfile = os.path.join(options.outputdir, "%s-serial.pickle"  % identifier)  # memory dump
    debugfile  = os.path.join(options.outputdir, "%s-debug.txt"      % identifier)  # human readable memory dump
    ndl24file  = os.path.join(options.outputdir, "%s-config.rdf"     % identifier)  # All information in latest NDL
    staticfile = os.path.join(options.outputdir, "%s-interfaces.rdf" % identifier)  # Static interface configuration in NDL (no configuration info)
    ndl22file  = os.path.join(options.outputdir, "%s-v22.rdf"        % identifier)  # NDL v2.2 deprecated version with all info
    devdotfile = os.path.join(options.outputdir, "%s-device.dot"     % identifier)  # Graph with vertices for devices
    ifdotfile  = os.path.join(options.outputdir, "%s-interface.dot"  % identifier)  # Graph with vertices for interfaces
    iologfile  = options.iologfile                # file to log raw I/O communications with devices
    passwdfile = options.configfile               # file with usernames and passwords
    errorlog = pynt.logger.Logger(errorfile, verbosity=options.verbosity)
    
    try:
        if options.simulate in ["pickle", "memory"]:
            if options.inputfilename:
                fetcher = pynt.input.serial.SerialInput(options.inputfilename)
            else:
                fetcher = pynt.input.serial.SerialInput(serialfile)
        else:
            namespaceuri = "http://%s#" % hostname
            identifier   = hostname.split(".")[0].capitalize()
            fetcher = fetcherclass(hostname, nsuri=namespaceuri, identifier=identifier)
            if options.simulate in ["command"]:
                logger.log(25, "Performing simulated query on %s" % hostname)
                if options.inputfilename:
                    fetcher.setSourceFile(options.inputfilename, hostname=hostname) # hostname is used to set prompt
                else:
                    fetcher.setSourceFile(iologfile, hostname=hostname)             # hostname is used to set prompt
            else:
                logger.log(25, "Performing live query on %s" % hostname)
                fetcher.setSourceHost(hostname, port=options.port)
            userpwd = pynt.input.usernames.GetLoginSettings(hostname, options.username, options.password, passwdfile)
            fetcher.io.setLoginCredentials(**userpwd)
            if iologfile:
                fetcher.io.setLogFile(iologfile)
        
        # fetches data from device and returns object structure.
        # The subject is something that can be passed on to BaseOutput.output();
        # Typically a Device object or namespace.
        subject = fetcher.getSubject()
        
        if not options.simulate:
            out = pynt.output.serial.SerialOutput(serialfile)
            out.output(subject)
        
        out = pynt.output.debug.DebugOutput(debugfile)
        out.output()
        
        out = pynt.output.manualrdf.RDFOutput(ndl24file)
        out.setMetaData("description", 'Configuration of the %s switch at Netherlight. This file is semi-dynamically generated by a cron job that logs in the devices and retrieves all information. You should expect this data to be stale for about 5 minutes. If you really need real-time data, then don\'t use NDL, but another mechanism (e.g. a routing protocol).' % subject.getName())
        out.setMetaData("publicationdate", '2007-01-31')
        out.output(subject)
        
        #out.setOutputFile(None) # set to STDOUT
        #out.output(force10)
        
        out.setOutputFile(staticfile)
        out.setPrintConfigured(False)
        out.setMetaData("description", 'Configuration of the %s switch at Netherlight. This file is automatically generated by a script that logs in the devices and all static information. This file does NOT contain dynamic information.' % subject.getName())
        out.setMetaData("publicationdate", '2007-01-31')
        out.output(subject)
        
        out = pynt.output.manualrdf.RDFv22Output(ndl22file)
        out.output(subject)
        
        out = pynt.output.dot.DeviceGraphOutput(devdotfile)
        out.output(subject)
        
        out = pynt.output.dot.InterfaceGraphOutput(ifdotfile)
        out.output(subject)
        
    except:  # *any* kind of exception, including user-interupts, etc.
        # the write functions are atomic, so those will be fine when an exception occurs
        errorlog.logException()
        (exceptionclass, exception, traceback) = sys.exc_info()
        logger.exception("")
    
    # We check if an error occured
    # if so, we do nothing, and keep the existing files. Those should still be valid.
    # However, if we previously also had errors, this is probably more fundamental.
    # In that case, we replace the -cache file with the -static file, effectively 
    # removing all dynamic data from the RDF files.
    if errorlog.getCurErrorCount() and errorlog.getPrevErrorCount():
        logger.info("Two errors in a row. Overwriting %s with %s" % (ndl24file, staticfile))
        try:
            pynt.output.CopyFile(staticfile, ndl24file)
        except IOError:
            pass
    
