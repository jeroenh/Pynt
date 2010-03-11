#!/usr/bin/env python
# -*- coding: utf-8 -*-

# standard modules
import sys
import os.path
import logging
import re
import pyclbr # class browser, which is safe for malicious code (it is not executed)
import optparse

# local modules
import pynt.elements
import pynt.layers
import pynt.input.commandline
import pynt.xmlns
import pynt.algorithm
import pynt.algorithm.output
import pynt.output.dot

# Helper script to create a network with the GLIF example pynt.
# The network is specifically created to demonstrate multi-layer path finding.
import glifcreate
import glifsimplecreate
import ethcreate


class ProgressDotOutput(pynt.output.dot.InterfaceGraphOutput):
    count = 0
    path  = None
    color = "#ffffff"
    networkType = ""
    
    def inPath(self, interface1, interface2, connectiontype):
        """Return True if the connection from interface1 to interface2 is part of self.path"""
        if (not self.path) or (len(self.path) <= 1):
            return 0
        count = 0
        for hop in range(1,len(self.path)):
            if (self.path[hop-1].cp == interface1) and \
                    (self.path[hop].cp == interface2) and \
                    isinstance(self.path[hop].prevconnection, connectiontype):
                count += 1
        return count
    
    def inPathSwitchMatrix(self, interface):
        """Return True if the connection from interface to the previous or the next goes to a switch matrix"""
        if (not self.path) or (len(self.path) <= 1):
            return 0
        count = 0
        for hop in range(1,len(self.path)):
            # Look to see if this interface is in the path
            if (self.path[hop-1].cp == interface): 
                # Is the switch matrix of this interface the same of the
                # next interface
                if (interface.getSwitchMatrix() ==  self.path[hop].cp.getSwitchMatrix()):
                    count += 1
                # Now, we need to draw 'backward', so:
                # Was the switchmatrix of this interface the same of the
                # preceding interface? 
                if (interface.getSwitchMatrix() == self.path[hop-2].cp.getSwitchMatrix()):
                    count += 1
        return count
    
    def printHeader(self):
        super(ProgressDotOutput, self).printHeader()
        #if self.count:
        #    self.write('"counter_label" [label="%s", fontsize=40];' % (self.count))
        
    def getStyle(self, basestyle, inpathcount, colour):
        """Return the dot style for a link which is inpathcount number of times part of the path.
        Colour is only used if inpathcount > 0"""
        if inpathcount > 0:
            basestyle += ', color="%s", style="setlinewidth(%d)"' % (colour, -1+4*inpathcount)
        return basestyle
    
    def printInterface(self, interface):
        """Note: printInterface prints the edges in the dot file. 
        The interfaces itself are printed in printDevice, so interfaces without devices are never printed; 
        yes, that's a bug.)"""
        # * linkTo, connectedTo: directed edge with open arrow
        for peer in interface.getConnectedInterfaces(): # including link to
            inpathcount = self.inPath(interface, peer, pynt.paths.ConnectedToConnection)
            style = self.getStyle("arrowhead=open", inpathcount, self.color)
            self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), peer.getURIdentifier(), style))
        # * adaptation: directed edge with empty arrow
        for (peer,adaptationfunction) in interface.getAllServerTuples():
            inpathcount = self.inPath(interface, peer, pynt.paths.AdaptationConnection)
            style = 'arrowhead=empty, label="%s", adaptation="%s"' % (adaptationfunction.getName(), adaptationfunction.getURIdentifier())
            style = self.getStyle(style, inpathcount, self.color)
            self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), peer.getURIdentifier(), style))
        # * de-adaptation: directed edge with invempty arrow
        for (peer,adaptationfunction) in interface.getAllClientTuples():
            inpathcount = self.inPath(interface, peer, pynt.paths.DeAdaptationConnection)
            style = 'arrowhead=invempty, adaptation="%s"' % (adaptationfunction.getURIdentifier())
            style = self.getStyle(style, inpathcount, self.color)
            self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), peer.getURIdentifier(), style))
        # * part of switch matrix: *uni*directed edge with odiamond arrows (in both directions)
        # * switchTo: directed edge with diamond arrow
        switchmatrix = interface.getSwitchMatrix()
        if switchmatrix:
            # I would have expected to see non empty values in the list returned by:
            # switchmatrix.getActualSwitchedInterfaces(interface)
            # interface.getDirectlySwitchedInterfaces()
            # but it is not. So I use the following function to see if the path needs to be colored
            inpathcount = self.inPathSwitchMatrix(interface)
            style = 'dir=both, arrowtail=diamond, arrowhead=odiamond'
            style = self.getStyle(style, inpathcount, self.color)
            self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), switchmatrix.getURIdentifier(), style))
        else: 
            for peer in interface.getActualSwitchedInterfaces():
                inpathcount = self.inPath(interface,peer,pynt.paths.SwitchToConnection)
                style = 'arrowhead=diamond'
                style = self.getStyle(style, inpathcount, self.color)
                self.write('"%s" -> "%s" [%s];' % (interface.getURIdentifier(), peer.getURIdentifier(), style))
    
    def printFooter(self):
        # self.write('"network_name_label" [label="%s", fontsize=40];' % (self.networkType))
        if self.networkType in ["glif", "glifalt"]:
            self.write('hiddenManLanDevice -> hiddenCANetDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenStarLightDevice -> hiddenCANetDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenStarLightDevice -> hiddenManLanDevice [ weight=100, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenManLanDevice -> hiddenNetherLightDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenUvADevice -> hiddenNetherLightDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
            self.write('hiddenQuebecEthernetDevice -> hiddenCANetDevice [ weight=9999, len=1, color = "#ffffff", arrowhead=none, style="setlinewidth(0)"];')
        self.indent -= 1
        self.write("}")
    
    def setNetworkType(self, network):
        self.networkType = network
    


class PathFindDemo(object):
    namespaces      = None  # List of involved namespaces
    sourcecp        = None  # source interface
    destinationcp   = None  # destination interface


def CreateNetworkFromFile(filename):
    pfdemo = PathFindDemo()
    fetcher = pynt.input.rdf.RDFNetworkFetcher(filename)
    subject = fetcher.getSubject()
    print subject
    
    #pfdemo.namespaces   = ethcreate.DefineNetwork()
    #exns                = pynt.xmlns.GetCreateNamespace("http://example.net/#")
    #pfdemo.sourcecp     = pynt.xmlns.GetRDFObject("Ford",   namespace=exns, klass=pynt.elements.ConnectionPoint)
    #pfdemo.destinationcp= pynt.xmlns.GetRDFObject("Zaphod", namespace=exns, klass=pynt.elements.ConnectionPoint)
    return pfdemo

def GlifCreate():
    pfdemo = PathFindDemo()
    glifcreate.ReadTechnologies()
    pfdemo.namespaces   = glifcreate.DefineNetwork()
    uqamns              = pynt.xmlns.GetCreateNamespace("http://uqam.ca/#")
    uvans               = pynt.xmlns.GetCreateNamespace("http://uva.nl/#")
    starlns             = pynt.xmlns.GetCreateNamespace("http://starlight.org/#")
    canetns             = pynt.xmlns.GetCreateNamespace("http://canarie.ca/#")
    pfdemo.sourcecp     = pynt.xmlns.GetRDFObject("if1-eth", namespace=uqamns, klass=pynt.elements.ConnectionPoint)
    pfdemo.destinationcp= pynt.xmlns.GetRDFObject("if8-eth", namespace=uvans,  klass=pynt.elements.ConnectionPoint)
    return pfdemo

def GlifAltCreate():
    pfdemo = PathFindDemo()
    glifsimplecreate.ReadTechnologies()
    pfdemo.namespaces   = glifsimplecreate.DefineNetwork()
    uqamns              = pynt.xmlns.GetCreateNamespace("http://uqam.ca/#")
    uvans               = pynt.xmlns.GetCreateNamespace("http://uva.nl/#")
    starlns             = pynt.xmlns.GetCreateNamespace("http://starlight.org/#")
    canetns             = pynt.xmlns.GetCreateNamespace("http://canarie.ca/#")
    pfdemo.sourcecp     = pynt.xmlns.GetRDFObject("if1-eth", namespace=uqamns, klass=pynt.elements.ConnectionPoint)
    pfdemo.destinationcp= pynt.xmlns.GetRDFObject("if8-eth", namespace=uvans,  klass=pynt.elements.ConnectionPoint)
    return pfdemo

def EthCreate():
    pfdemo = PathFindDemo()
    ethcreate.ReadTechnologies()
    pfdemo.namespaces   = ethcreate.DefineNetwork()
    exns                = pynt.xmlns.GetCreateNamespace("http://example.net/#")
    pfdemo.sourcecp     = pynt.xmlns.GetRDFObject("Ford",   namespace=exns, klass=pynt.elements.ConnectionPoint)
    pfdemo.destinationcp= pynt.xmlns.GetRDFObject("Zaphod", namespace=exns, klass=pynt.elements.ConnectionPoint)
    return pfdemo

def getAlgorithmClassByName(name=None):
    # This can be a lot faster. See e.g. unittest loadTestsFromName() (use split('.'), __import__(), and getattr())
    logger = logging.getLogger("pynt.algorithm")
    algClass = pynt.algorithm.BaseAlgorithm  # default class
    modulename = "pynt.algorithm"            # default module
    if name == None:
        return algClass
    matches = re.compile("^((\w+\.)*)(\w+)$").match(name)
    if matches == None:
        logger.error("%s is not a valid module name. Revert to default algorithm %s" % (modulename, algClass.__name__))
    if matches.group(1):
        modulename = matches.group(1)
    name = matches.group(3)
    try:
        algmod = pyclbr.readmodule(modulename)
    except (TypeError, ValueError):
        logger.error("%s is not a valid module. Revert to default algorithm %s" % (modulename, algClass.__name__))
        return algClass
    if name not in algmod:
        logger.error("Class %s is not found in module %s. Revert to default algorithm %s" % (name, modulename, algClass.__name__))
        return algClass
    alg = algmod[name]
    try:
        module = __import__(modulename)
        # Get the child module for modulenames with a dot (by default __import__(a.b) returns module a).
        components = modulename.split('.')
        for comp in components[1:]:
            module = getattr(module, comp)
    except ImportError:
        logger.error("Can not import module %s. Revert to default algorithm %s" % (modulename, algClass.__name__))
        return algClass
    try:
        customAlgClass = getattr(module, name)
    except AttributeError, e:
        logger.error("Can not instantiate %s.%s: %s. Revert to default algorithm %s" % (modulename, name, e, algClass.__name__))
        return algClass
    if not isinstance(customAlgClass, type) or not issubclass(customAlgClass, pynt.algorithm.BaseAlgorithm):
        logger.error("Class %s is not a valid algorithm class. Revert to default algorithm %s" % (customAlgClass.__name__, algClass.__name__))
        return algClass
    return customAlgClass

def GetDefaultOutputDir():
    # default is 'ndl/output/' if it exists, otherwise './'.
    if os.path.exists('output'):
        return 'output'
    elif os.path.exists('../output'):
        return '../output'
    elif os.path.exists(os.path.join(os.path.dirname(os.path.realpath(pynt.__file__)), '..', 'output')):
        return os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(pynt.__file__)), '..', 'output'))
    else:
        return '.'

def GetOptions(argv=None):
    """
    Parse command line arguments.
    """
    if argv is None:
        # allow user to override argv in interactive python interpreter
        argv = sys.argv
    parser = optparse.OptionParser(conflict_handler="resolve")
    # standard option: -h and --help to display these options
    parser.add_option("-o", "--output", dest="outputdir", action="store", type="string", metavar="PATH", 
                      help="The directory to store the output files", default=GetDefaultOutputDir())
    parser.add_option("-v", "--verbose", dest="verbosity", action="count", default=0, 
                      help="Verbose output (multiple -v makes it even chattier)")
    parser.add_option("-q", "--quiet", dest="quietness", action="count", default=0, 
                      help="Quiet output (multiple -q makes it even more silent)")
    parser.add_option("-d", dest="dotprogress", action="store_true", default=False,
                      help="Generate dot output during algorithm progress")
    parser.add_option("-n", dest="demoNet", action="store", default='glifalt',
                      help="Specify which network is going to be generated")
    parser.add_option("-f", dest="filename", action="store", default=None,
                      help="Specify file with network description")
    parser.add_option("--src", "--source", dest="sourceuri", action="store",  metavar="SOURCE", default=None,
                      help="URI of source interface")
    parser.add_option("--dst", "--dest", dest="destinationuri", action="store",  metavar="DEST", default=None,
                      help="URI of destination interface")
    parser.add_option("-a", "--alogrithm", dest="algorithm", action="store", default="PFAvailable",
                      help="The name of the algorithm to use")
    parser.add_option("-c", "--consecutive", dest="consecutive", action="store_true",
                      help="Write output in consecutive files")
    parser.add_option("-s", "--step", dest="stepsize", action="store",type="int", default=1, 
                      help="The stepsize for the consecutive output files (default=1)")
    (options, args) = parser.parse_args(args=argv[1:])
    options.verbosity -= options.quietness
    return (options, args)

def Main(argv=None):
    (options, args) = GetOptions(argv)
    
    # Read network
    pynt.logger.SetLogLevel(min(0, options.verbosity))
    logger = logging.getLogger("pynt.algorithm")
    # Do not log this with verbosity > 0.
    # Network generation function, returning start and destination interface
    # Determine which network needs to be generated
    if options.filename != None:
        pynt.logger.SetLogLevel(options.verbosity)
        pfdemo = CreateNetworkFromFile(options.filename)
    elif options.demoNet == 'glif':
        logger.info("Select GLIF sample network to generate")
        pfdemo = GlifCreate()
    elif options.demoNet == 'glifalt':
        logger.info("Select GLIF alternative sample network to generate")
        pfdemo = GlifAltCreate()
    elif options.demoNet == 'eth':
        logger.info("Select ethernet sample network to generate")
        pfdemo = EthCreate()
    else:
        logger.error("Unknown network to generate")
        return
    # Now, verbosity may be increased
    pynt.logger.SetLogLevel(options.verbosity)
    
    # Instantiate algorithm
    algorithmclass = getAlgorithmClassByName(options.algorithm)
    logger.log(25, "Using %s to find a path from %s to %s" % (algorithmclass.__name__, pfdemo.sourcecp.getURIdentifier(), pfdemo.destinationcp.getURIdentifier()))
    algorithm = algorithmclass()
    algorithm.setEndpoints(pfdemo.sourcecp, pfdemo.destinationcp)
    
    # Set output printers
    if options.verbosity <= -3:
        algorithm.setPrinter(pynt.algorithm.output.NoPrinter()) # no output ever
    elif options.verbosity <= -2:
        algorithm.setPrinter(pynt.algorithm.output.ResultTextPrinter()) # no progress output, only a final result
    elif options.verbosity <= 0:
        algorithm.setPrinter(pynt.algorithm.output.SimpleTextProgressPrinter()) # dots as progress
    else:
        algorithm.setPrinter(pynt.algorithm.output.TextProgressPrinter()) # verbose output
    if options.consecutive:
        output = ProgressDotOutput(os.path.join(options.outputdir, "pathfind.dot"))
        output.setNetworkType(options.demoNet)
        dotprogressprinter = pynt.algorithm.output.MultiFilePrinter(output, pfdemo.namespaces, options.stepsize)
        algorithm.addPrinter(dotprogressprinter)
    if options.dotprogress:
        output = ProgressDotOutput(os.path.join(options.outputdir, "pathfind.dot"))
        output.setNetworkType(options.demoNet)
        if options.stepsize == 0: # only print the final result
            dotprogressprinter = pynt.algorithm.output.SingleFilePrinter(output, pfdemo.namespaces)
        else: # print eahc individual step
            dotprogressprinter = pynt.algorithm.output.OverwriteFilePrinter(output, pfdemo.namespaces, options.stepsize)
        algorithm.addPrinter(dotprogressprinter)
    
    solutions = algorithm.findShortestPath()
    algorithm.printSolution()


if __name__=="__main__":
    Main()
