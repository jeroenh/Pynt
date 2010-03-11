#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import optparse
import pynt.input.idc
import logging

# import pynt.technologies.ethernet
import pynt.input.rdf
import pynt.output.debug
import pynt.output.manualrdf
import pynt.output.dot
import pynt.output.idc

def Main():
    """docstring for Main"""
    ndlfile = pynt.input.rdf.RDFSchemaFetcher("output/idc-config.rdf")
    ndlfile.fetch()  # fetches data from RDF schema
    output = pynt.output.dot.InterfaceGraphOutput('ndl-reader.dot')
    output.output()
    

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
    Main()