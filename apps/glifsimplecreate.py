#!/usr/bin/env python
# -*- coding: utf-8 -*-

# standard modules
import sys
import logging
import os.path
# local modules
import pynt.elements
import pynt.xmlns
import pynt.input.rdf
import pynt.output.manualrdf
import pynt.output.debug
import pynt.output.dot
import pynt.output.rdf

import pynt.logger
import pynt.input.commandline

# Helper script to create a network with the GLIF example pynt.
# The network is specifically created to demonstrate multi-layer path finding.

def Main(argv=None):
    (options, args) = pynt.input.commandline.GetOptions(argv)
    pynt.logger.SetLogLevel(options.verbosity)
    
    ReadTechnologies()
    domains = DefineNetwork()
    WriteToFiles(domains, outputdir=options.outputdir)

def ReadTechnologies():
    path = os.path.realpath(os.path.normpath(os.path.join(os.path.dirname(__file__), '../schema/rdf')))
    if not os.path.isdir(path):
        path = 'http://www.science.uva.nl/research/sne/schema'
    fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/ethernet.rdf")
    fetcher.fetch()
    fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/tdm-alt.rdf")
    fetcher.fetch()
    fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/wdm.rdf")
    fetcher.fetch()
    fetcher = pynt.input.rdf.RDFLayerSchemaFetcher(path+"/copper.rdf")
    fetcher.fetch()

def DefineNetwork():
    # - Quebec         1 physical interface: Ethernet
    # - CAnet          3 physical interface: Ethernet, SONET (2x), 1 Switch Matrix (SONET, switching, no swapping); 1 fixed switchedTo outside matrix (for Ethernet in SONET)
    # - StarLight      2 physical interfaces: SONET/Ethernet, 2 Switch Matrices (SONET, switching and swapping and Ethernet, broadcast)
    # - MANLAN         4 physical interfaces: SONET, 1 Switch Matrix (SONET, switching and swapping)
    # - NetherLight    3 physical interface: Ethernet, SONET (2x), 1 Switch Matrix (SONET, switching, no swapping); 1 fixed switchedTo outside matrix (for Ethernet in SONET)
    # - Amsterdam      1 physical interface: Ethernet
    
    domainNamespaces = []
    
    # Get all namespaces, layers and adaptations.
    
    ethns       = pynt.xmlns.GetNamespaceByPrefix("ethernet")
    tdmaltns    = pynt.xmlns.GetNamespaceByPrefix("tdmalt")
    tdmns       = pynt.xmlns.GetNamespaceByURI("http://www.science.uva.nl/research/sne/ndl/tdm#")
    wdmns       = pynt.xmlns.GetNamespaceByPrefix("wdm")
    copperns    = pynt.xmlns.GetNamespaceByPrefix("copper")
    
    ethlayer    = pynt.xmlns.GetRDFObject("EthernetNetworkElement",      namespace=ethns,    klass=pynt.layers.Layer)
    vc4layer    = pynt.xmlns.GetRDFObject("VC4NetworkElement",           namespace=tdmaltns, klass=pynt.layers.Layer)
    oclayer     = pynt.xmlns.GetRDFObject("OC192NetworkElement",         namespace=tdmns,    klass=pynt.layers.Layer)
    lambdalayer  = pynt.xmlns.GetRDFObject("LambdaNetworkElement",       namespace=wdmns,    klass=pynt.layers.Layer)
    fiberlayer  = pynt.xmlns.GetRDFObject("FiberNetworkElement",         namespace=wdmns,    klass=pynt.layers.Layer)
    utplayer    = pynt.xmlns.GetRDFObject("TwistedPairNetworkElement",   namespace=copperns, klass=pynt.layers.Layer)
    
    ethin7vc4   = pynt.xmlns.GetRDFObject("GiEthernet-in-7-VC4",         namespace=tdmaltns, klass=pynt.layers.AdaptationFunction)
    ethin8vc4   = pynt.xmlns.GetRDFObject("GiEthernet-in-8-VC4",         namespace=tdmaltns, klass=pynt.layers.AdaptationFunction)
    stsinoc     = pynt.xmlns.GetRDFObject("STS-in-OC192",                namespace=tdmaltns, klass=pynt.layers.AdaptationFunction)
    ocinlambda  = pynt.xmlns.GetRDFObject("oc192-in-Lambda",             namespace=wdmns,    klass=pynt.layers.AdaptationFunction)
    lambdainfiber = pynt.xmlns.GetRDFObject("WDM",                       namespace=wdmns,    klass=pynt.layers.AdaptationFunction)
    ethinutp    = pynt.xmlns.GetRDFObject("base-T",                      namespace=copperns, klass=pynt.layers.AdaptationFunction)
    ethinlambda = pynt.xmlns.GetRDFObject("eth1000base-X",               namespace=wdmns,    klass=pynt.layers.AdaptationFunction)
    
    logger = logging.getLogger("network")
    logger.log(25, "Building demo GLIF network in memory")
    
    vc4range    = pynt.rangeset.RangeSet("1-64", itemtype=int, interval=1)
    # link 1: VC-4 (fixed label: 31)
    link1label = 31
    link1range = pynt.rangeset.RangeSet(31, itemtype=int, interval=1)
    # link 2: Potential VC-4 (7 free labels)   # must have 42, must not have 31
    link2label = 12
    link2range = pynt.rangeset.RangeSet("2,12-16,42", itemtype=int, interval=1)
    link2sl    = pynt.rangeset.RangeSet(42, itemtype=int, interval=1)
    assert(len(link2range) == 7)
    assert(len(link1range + link2range) > 0)
    assert(len(link1range & link2sl) == 0)
    # link 3: Potential VC-4 (13 free labels)
    link3label = 42
    link3sl    = pynt.rangeset.RangeSet(42, itemtype=int, interval=1)
    link3range = pynt.rangeset.RangeSet("3,10-14,34-39,42", itemtype=int, interval=1)
    assert(len(link3range) == 13)
    # link 4: Potential VC-4 (20 free labels)  # must have 31, 42, multiple of link 2
    link4label = 14
    link4range = pynt.rangeset.RangeSet("14-24,31-35,41-44", itemtype=int, interval=1)
    assert(len(link4range) == 20)
    assert(len(link4range & link2range) > 1)
    assert(len(link4range & link1range) > 0)
    # link 5: Potential VC-4 (9 free labels)  # must have 31, 42, multiple of link 2
    #link5label = 15
    #link5range = pynt.rangeset.RangeSet("15-20,31,42,55", itemtype=int, interval=1)
    #assert(len(link5range) == 9)
    #assert(len(link5range & link2range) > 1)
    #assert(len(link5range & link1range) > 0)
    # link 6: Potential VC-4 (10 free labels)
    link6label = 16
    link6range = pynt.rangeset.RangeSet("16-19,28,41-45", itemtype=int, interval=1)
    assert(len(link6range) == 10)
    # link 7: Potential VC-4 (11 free labels)  # should not have 42
    link7label = 17
    link7range = pynt.rangeset.RangeSet("17,24-28,53-57", itemtype=int, interval=1)
    assert(len(link7range) == 11)
    # link 8: VC-4 (fixed label: 28)
    link8label = 28
    link8range = pynt.rangeset.RangeSet(28, itemtype=int, interval=1)
    
    # 
    # Université de Quebec:
    # 
    
    uqamns          = pynt.xmlns.GetCreateNamespace("http://uqam.ca/#")
    domainNamespaces.append(uqamns)
    uqamdev         = pynt.elements.GetCreateDevice("QuebecEthernetDevice", namespace=uqamns)
    uqamdev.setName("Quebec")
    
    # if1: Ethernet over UTP
    uqamif1utp      = pynt.xmlns.CreateRDFObject("if1-utp", namespace=uqamns, klass=pynt.elements.StaticInterface)
    uqamif1utp.setLayer(utplayer)
    uqamif1utp.setDevice(uqamdev)
    uqamif1eth      = pynt.xmlns.CreateRDFObject("if1-eth", namespace=uqamns, klass=pynt.elements.StaticInterface)
    uqamif1eth.setLayer(ethlayer)
    uqamif1eth.setDevice(uqamdev)
    uqamif1utp.addClientInterface(uqamif1eth, ethinutp)
    
    # no switch matrix
    
    # 
    # CA*net:
    # 
    
    canetns         = pynt.xmlns.GetCreateNamespace("http://canarie.ca/#")
    domainNamespaces.append(canetns)
    canetdev        = pynt.elements.GetCreateDevice("CANetDevice", namespace=canetns)
    canetdev.setName("CA*net")
    
    # if1 (a): Ethernet over UTP
    # if1 (b): Ethernet over (8-variant) VC-4 (fixed label: 31)
    # if1 (c): VC-4
    canetif1aeth    = pynt.xmlns.CreateRDFObject("if1a-eth", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif1aeth.setLayer(ethlayer)
    canetif1aeth.setDevice(canetdev)
    canetif1autp    = pynt.xmlns.CreateRDFObject("if1a-utp", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif1autp.setLayer(utplayer)
    canetif1autp.setDevice(canetdev)
    canetif1autp.addClientInterface(canetif1aeth, ethinutp)
    
    canetif1beth    = pynt.xmlns.CreateRDFObject("if1b-eth", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif1beth.setLayer(ethlayer)
    canetif1beth.setDevice(canetdev)
    canetif1bvc4    = pynt.xmlns.CreateRDFObject("if1b-vc4", namespace=canetns, klass=pynt.elements.ConfigurableInterface)
    canetif1bvc4.setLayer(vc4layer)
    canetif1bvc4.setDevice(canetdev)
    canetif1bvc4.setLabel(link1label)
    canetif1bvc4.setLabelSet(link1range)
    canetif1bvc4.addClientInterface(canetif1beth, ethin8vc4)
    
    canetif1aeth.addSwitchedInterface(canetif1beth)
    canetif1beth.addSwitchedInterface(canetif1aeth)
    
    canetif1cvc4    = pynt.xmlns.CreateRDFObject("if1c-vc4", namespace=canetns, klass=pynt.elements.ConfigurableInterface)
    canetif1cvc4.setLayer(vc4layer)
    canetif1cvc4.setDevice(canetdev)
    canetif1cvc4.setLabel(link1label)
    canetif1cvc4.setLabelSet(vc4range)
    
    canetif1bvc4.addLinkedInterface(canetif1cvc4)
    canetif1cvc4.addLinkedInterface(canetif1bvc4)
    
    # if2: Potential VC-4 (22 free labels) over OC over Lambda over Fiber
    canetif2vc4     = pynt.xmlns.CreateRDFObject("if2-vc4", namespace=canetns, klass=pynt.elements.PotentialMuxInterface)
    canetif2vc4.setLayer(vc4layer)
    canetif2vc4.setDevice(canetdev)
    #canetif2vc4.setLabel(link2label)
    canetif2vc4.setLabelSet(link2range)
    canetif2oc     = pynt.xmlns.CreateRDFObject("if2-oc", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif2oc.setLayer(oclayer)
    canetif2oc.setDevice(canetdev)
    canetif2lambda = pynt.xmlns.CreateRDFObject("if2-lambda", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif2lambda.setLayer(lambdalayer)
    canetif2lambda.setDevice(canetdev)
    canetif2lambda.setLabel(1310.0)
    canetif2fiber  = pynt.xmlns.CreateRDFObject("if2-fiber", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif2fiber.setLayer(fiberlayer)
    canetif2fiber.setDevice(canetdev)
    canetif2fiber.addClientInterface(canetif2lambda, lambdainfiber)
    canetif2lambda.addClientInterface(canetif2oc, ocinlambda)
    canetif2oc.addClientInterface(canetif2vc4, stsinoc)
    
    # if4: Potential VC-4 (61 free labels) over OC over Lambda over Fiber
    canetif4vc4     = pynt.xmlns.CreateRDFObject("if4-vc4", namespace=canetns, klass=pynt.elements.PotentialMuxInterface)
    canetif4vc4.setLayer(vc4layer)
    canetif4vc4.setDevice(canetdev)
    #canetif4vc4.setLabel(link4label)
    canetif4vc4.setLabelSet(link4range)
    canetif4oc     = pynt.xmlns.CreateRDFObject("if4-oc", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif4oc.setLayer(oclayer)
    canetif4oc.setDevice(canetdev)
    canetif4lambda = pynt.xmlns.CreateRDFObject("if4-lambda", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif4lambda.setLayer(lambdalayer)
    canetif4lambda.setDevice(canetdev)
    canetif4lambda.setLabel(1310.0)
    canetif4fiber  = pynt.xmlns.CreateRDFObject("if4-fiber", namespace=canetns, klass=pynt.elements.StaticInterface)
    canetif4fiber.setLayer(fiberlayer)
    canetif4fiber.setDevice(canetdev)
    canetif4fiber.addClientInterface(canetif4lambda, lambdainfiber)
    canetif4lambda.addClientInterface(canetif4oc, ocinlambda)
    canetif4oc.addClientInterface(canetif4vc4, stsinoc)
    
    # if5: Potential VC-4 (26 free labels) over OC over Lambda over Fiber
    #canetif5vc4     = pynt.xmlns.CreateRDFObject("if5-vc4", namespace=canetns, klass=pynt.elements.PotentialMuxInterface)
    #canetif5vc4.setLayer(vc4layer)
    #canetif5vc4.setDevice(canetdev)
    ##canetif5vc4.setLabel(link5label)
    #canetif5vc4.setLabelSet(link5range)
    #canetif5oc     = pynt.xmlns.CreateRDFObject("if5-oc", namespace=canetns, klass=pynt.elements.StaticInterface)
    #canetif5oc.setLayer(oclayer)
    #canetif5oc.setDevice(canetdev)
    #canetif5lambda = pynt.xmlns.CreateRDFObject("if5-lambda", namespace=canetns, klass=pynt.elements.StaticInterface)
    #canetif5lambda.setLayer(lambdalayer)
    #canetif5lambda.setDevice(canetdev)
    #canetif5lambda.setLabel(1310.0)
    #canetif5fiber  = pynt.xmlns.CreateRDFObject("if5-fiber", namespace=canetns, klass=pynt.elements.StaticInterface)
    #canetif5fiber.setLayer(fiberlayer)
    #canetif5fiber.setDevice(canetdev)
    #canetif5fiber.addClientInterface(canetif5lambda, lambdainfiber)
    #canetif5lambda.addClientInterface(canetif5oc, ocinlambda)
    #canetif5oc.addClientInterface(canetif5vc4, stsinoc)
    
    # VC-4 Switch Matrix, only switching (no swapping)
    
    canetsw     = pynt.elements.GetCreateSwitchMatrix("CAnetSwitchMatrix", namespace=canetns)
    canetsw.setLayer(vc4layer)
    canetsw.setDevice(canetdev)
    canetsw.setSwitchingCapability(True)
    canetsw.setSwappingCapability(False)
    canetsw.setUnicast(True)
    canetsw.addInterface(canetif1cvc4)
    canetsw.addInterface(canetif2vc4)
    canetsw.addInterface(canetif4vc4)
    #canetsw.addInterface(canetif5vc4)
    switchmatrix = canetif1cvc4.getSwitchMatrix()
    
    # 
    # StarLight
    # 
    
    starlns     = pynt.xmlns.GetCreateNamespace("http://starlight.org/#")
    domainNamespaces.append(starlns)
    starldev    = pynt.elements.GetCreateDevice("StarLightDevice", namespace=starlns)
    starldev.setName("StarLight")
    
    # if2: Potential Ethernet over (either 7 or 8 variant) Potential? VC-4 (fixed label: 42) over OC over Lambda over Fiber
    starlif2eth7    = pynt.xmlns.CreateRDFObject("if2-eth7", namespace=starlns, klass=pynt.elements.PotentialMuxInterface)
    starlif2eth7.setLayer(ethlayer)
    starlif2eth7.setDevice(starldev)
    starlif2eth8    = pynt.xmlns.CreateRDFObject("if2-eth8", namespace=starlns, klass=pynt.elements.PotentialMuxInterface)
    starlif2eth8.setLayer(ethlayer)
    starlif2eth8.setDevice(starldev)
    starlif2vc4     = pynt.xmlns.CreateRDFObject("if2-vc4", namespace=starlns, klass=pynt.elements.ConfigurableInterface)
    starlif2vc4.setLayer(vc4layer)
    starlif2vc4.setDevice(starldev)
    starlif2vc4.setLabel(link2label)
    starlif2vc4.setLabelSet(link2range)
    starlif2oc      = pynt.xmlns.CreateRDFObject("if2-oc", namespace=starlns, klass=pynt.elements.StaticInterface)
    starlif2oc.setLayer(oclayer)
    starlif2oc.setDevice(starldev)
    starlif2lambda  = pynt.xmlns.CreateRDFObject("if2-lambda", namespace=starlns, klass=pynt.elements.StaticInterface)
    starlif2lambda.setLayer(lambdalayer)
    starlif2lambda.setDevice(starldev)
    starlif2lambda.setLabel(1310.0)
    starlif2fiber   = pynt.xmlns.CreateRDFObject("if2-fiber", namespace=starlns, klass=pynt.elements.StaticInterface)
    starlif2fiber.setLayer(fiberlayer)
    starlif2fiber.setDevice(starldev)
    starlif2fiber.addClientInterface(starlif2lambda, lambdainfiber)
    starlif2lambda.addClientInterface(starlif2oc, ocinlambda)
    starlif2oc.addClientInterface(starlif2vc4, stsinoc)
    starlif2vc4.addClientInterface(starlif2eth7, ethin7vc4)
    starlif2vc4.addClientInterface(starlif2eth8, ethin8vc4)
    
    # if3: Potential Ethernet over (either 7 or 8 variant) Potential? VC-4 (fixed label: 42) over OC over Lambda over Fiber
    starlif3eth7    = pynt.xmlns.CreateRDFObject("if3-eth7", namespace=starlns, klass=pynt.elements.PotentialMuxInterface)
    starlif3eth7.setLayer(ethlayer)
    starlif3eth7.setDevice(starldev)
    starlif3eth8    = pynt.xmlns.CreateRDFObject("if3-eth8", namespace=starlns, klass=pynt.elements.PotentialMuxInterface)
    starlif3eth8.setLayer(ethlayer)
    starlif3eth8.setDevice(starldev)
    starlif3vc4     = pynt.xmlns.CreateRDFObject("if3-vc4", namespace=starlns, klass=pynt.elements.ConfigurableInterface)
    starlif3vc4.setLayer(vc4layer)
    starlif3vc4.setDevice(starldev)
    starlif3vc4.setLabel(link3label)
    starlif3vc4.setLabelSet(link3range)
    starlif3oc      = pynt.xmlns.CreateRDFObject("if3-oc", namespace=starlns, klass=pynt.elements.StaticInterface)
    starlif3oc.setLayer(oclayer)
    starlif3oc.setDevice(starldev)
    starlif3lambda  = pynt.xmlns.CreateRDFObject("if3-lambda", namespace=starlns, klass=pynt.elements.StaticInterface)
    starlif3lambda.setLayer(lambdalayer)
    starlif3lambda.setDevice(starldev)
    starlif3lambda.setLabel(1310.0)
    starlif3fiber   = pynt.xmlns.CreateRDFObject("if3-fiber", namespace=starlns, klass=pynt.elements.StaticInterface)
    starlif3fiber.setLayer(fiberlayer)
    starlif3fiber.setDevice(starldev)
    starlif3fiber.addClientInterface(starlif3lambda, lambdainfiber)
    starlif3lambda.addClientInterface(starlif3oc, ocinlambda)
    starlif3oc.addClientInterface(starlif3vc4, stsinoc)
    starlif3vc4.addClientInterface(starlif3eth7, ethin7vc4)
    starlif3vc4.addClientInterface(starlif3eth8, ethin8vc4)
    
    # Ethernet Switch Matrix, no labels (switching only)
    
    starlethsw     = pynt.elements.GetCreateSwitchMatrix("StarLightEthernetSwitchMatrix", namespace=starlns)
    starlethsw.setLayer(ethlayer)
    starlethsw.setDevice(starldev)
    starlethsw.setSwitchingCapability(True)
    starlethsw.setSwappingCapability(True)
    starlethsw.setUnicast(False)
    starlethsw.setBroadcast(True)
    starlethsw.addInterface(starlif2eth7)
    starlethsw.addInterface(starlif2eth8)
    starlethsw.addInterface(starlif3eth7)
    starlethsw.addInterface(starlif3eth8)
    
    # VC-4 Switch Matrix, switching and swapping
    
    starlvc4sw     = pynt.elements.GetCreateSwitchMatrix("StarLightVC-4SwitchMatrix", namespace=starlns)
    starlvc4sw.setLayer(vc4layer)
    starlvc4sw.setDevice(starldev)
    starlvc4sw.setSwitchingCapability(True)
    starlvc4sw.setSwappingCapability(True)
    starlvc4sw.setUnicast(True)
    starlvc4sw.addInterface(starlif2vc4)
    starlvc4sw.addInterface(starlif3vc4)
    
    # 
    # MAN LAN
    # 
    
    manlanns    = pynt.xmlns.GetCreateNamespace("http://manlan.internet2.edu/#")
    domainNamespaces.append(manlanns)
    manlandev   = pynt.elements.GetCreateDevice("ManLanDevice", namespace=manlanns)
    manlandev.setName("MAN LAN")
    
    # if3: Potential VC-4 (38 free labels) over OC over Lambda over Fiber
    manlanif3vc4     = pynt.xmlns.CreateRDFObject("if3-vc4", namespace=manlanns, klass=pynt.elements.PotentialMuxInterface)
    manlanif3vc4.setLayer(vc4layer)
    manlanif3vc4.setDevice(manlandev)
    #manlanif3vc4.setLabel(link3label)
    manlanif3vc4.setLabelSet(link3range)
    manlanif3oc     = pynt.xmlns.CreateRDFObject("if3-oc", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif3oc.setLayer(oclayer)
    manlanif3oc.setDevice(manlandev)
    manlanif3lambda = pynt.xmlns.CreateRDFObject("if3-lambda", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif3lambda.setLayer(lambdalayer)
    manlanif3lambda.setDevice(manlandev)
    manlanif3lambda.setLabel(1310.0)
    manlanif3fiber  = pynt.xmlns.CreateRDFObject("if3-fiber", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif3fiber.setLayer(fiberlayer)
    manlanif3fiber.setDevice(manlandev)
    manlanif3fiber.addClientInterface(manlanif3lambda, lambdainfiber)
    manlanif3lambda.addClientInterface(manlanif3oc, ocinlambda)
    manlanif3oc.addClientInterface(manlanif3vc4, stsinoc)
    
    # if4: Potential VC-4 (61 free labels) over OC over Lambda over Fiber
    manlanif4vc4     = pynt.xmlns.CreateRDFObject("if4-vc4", namespace=manlanns, klass=pynt.elements.PotentialMuxInterface)
    manlanif4vc4.setLayer(vc4layer)
    manlanif4vc4.setDevice(manlandev)
    #manlanif4vc4.setLabel(link4label)
    manlanif4vc4.setLabelSet(link4range)
    manlanif4oc     = pynt.xmlns.CreateRDFObject("if4-oc", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif4oc.setLayer(oclayer)
    manlanif4oc.setDevice(manlandev)
    manlanif4lambda = pynt.xmlns.CreateRDFObject("if4-lambda", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif4lambda.setLayer(lambdalayer)
    manlanif4lambda.setDevice(manlandev)
    manlanif4lambda.setLabel(1310.0)
    manlanif4fiber  = pynt.xmlns.CreateRDFObject("if4-fiber", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif4fiber.setLayer(fiberlayer)
    manlanif4fiber.setDevice(manlandev)
    manlanif4fiber.addClientInterface(manlanif4lambda, lambdainfiber)
    manlanif4lambda.addClientInterface(manlanif4oc, ocinlambda)
    manlanif4oc.addClientInterface(manlanif4vc4, stsinoc)
    
    ## if5: Potential VC-4 (26 free labels) over OC over Lambda over Fiber
    #manlanif5vc4     = pynt.xmlns.CreateRDFObject("if5-vc4", namespace=manlanns, klass=pynt.elements.PotentialMuxInterface)
    #manlanif5vc4.setLayer(vc4layer)
    #manlanif5vc4.setDevice(manlandev)
    ##manlanif5vc4.setLabel(link5label)
    #manlanif5vc4.setLabelSet(link5range)
    #manlanif5oc     = pynt.xmlns.CreateRDFObject("if5-oc", namespace=manlanns, klass=pynt.elements.StaticInterface)
    #manlanif5oc.setLayer(oclayer)
    #manlanif5oc.setDevice(manlandev)
    #manlanif5lambda = pynt.xmlns.CreateRDFObject("if5-lambda", namespace=manlanns, klass=pynt.elements.StaticInterface)
    #manlanif5lambda.setLayer(lambdalayer)
    #manlanif5lambda.setDevice(manlandev)
    #manlanif5lambda.setLabel(1310.0)
    #manlanif5fiber  = pynt.xmlns.CreateRDFObject("if5-fiber", namespace=manlanns, klass=pynt.elements.StaticInterface)
    #manlanif5fiber.setLayer(fiberlayer)
    #manlanif5fiber.setDevice(manlandev)
    #manlanif5fiber.addClientInterface(manlanif5lambda, lambdainfiber)
    #manlanif5lambda.addClientInterface(manlanif5oc, ocinlambda)
    #manlanif5oc.addClientInterface(manlanif5vc4, stsinoc)
    
    # if6: Potential VC-4 (30 free labels) over OC over Lambda over Fiber
    manlanif6vc4     = pynt.xmlns.CreateRDFObject("if6-vc4", namespace=manlanns, klass=pynt.elements.PotentialMuxInterface)
    manlanif6vc4.setLayer(vc4layer)
    manlanif6vc4.setDevice(manlandev)
    #manlanif6vc4.setLabel(link6label)
    manlanif6vc4.setLabelSet(link6range)
    manlanif6oc     = pynt.xmlns.CreateRDFObject("if6-oc", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif6oc.setLayer(oclayer)
    manlanif6oc.setDevice(manlandev)
    manlanif6lambda = pynt.xmlns.CreateRDFObject("if6-lambda", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif6lambda.setLayer(lambdalayer)
    manlanif6lambda.setDevice(manlandev)
    manlanif6lambda.setLabel(1310.0)
    manlanif6fiber  = pynt.xmlns.CreateRDFObject("if6-fiber", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif6fiber.setLayer(fiberlayer)
    manlanif6fiber.setDevice(manlandev)
    manlanif6fiber.addClientInterface(manlanif6lambda, lambdainfiber)
    manlanif6lambda.addClientInterface(manlanif6oc, ocinlambda)
    manlanif6oc.addClientInterface(manlanif6vc4, stsinoc)
    
    # if7: Potential VC-4 (33 free labels) over OC over Lambda over Fiber
    manlanif7vc4     = pynt.xmlns.CreateRDFObject("if7-vc4", namespace=manlanns, klass=pynt.elements.PotentialMuxInterface)
    manlanif7vc4.setLayer(vc4layer)
    manlanif7vc4.setDevice(manlandev)
    #manlanif7vc4.setLabel(link7label)
    manlanif7vc4.setLabelSet(link7range)
    manlanif7oc     = pynt.xmlns.CreateRDFObject("if7-oc", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif7oc.setLayer(oclayer)
    manlanif7oc.setDevice(manlandev)
    manlanif7lambda = pynt.xmlns.CreateRDFObject("if7-lambda", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif7lambda.setLayer(lambdalayer)
    manlanif7lambda.setDevice(manlandev)
    manlanif7lambda.setLabel(1310.0)
    manlanif7fiber  = pynt.xmlns.CreateRDFObject("if7-fiber", namespace=manlanns, klass=pynt.elements.StaticInterface)
    manlanif7fiber.setLayer(fiberlayer)
    manlanif7fiber.setDevice(manlandev)
    manlanif7fiber.addClientInterface(manlanif7lambda, lambdainfiber)
    manlanif7lambda.addClientInterface(manlanif7oc, ocinlambda)
    manlanif7oc.addClientInterface(manlanif7vc4, stsinoc)
    
    # VC-4 Switch Matrix, switching and swapping
    manlansw     = pynt.elements.GetCreateSwitchMatrix("ManLanSwitchMatrix", namespace=manlanns)
    manlansw.setLayer(vc4layer)
    manlansw.setDevice(manlandev)
    manlansw.setSwitchingCapability(True)
    manlansw.setSwappingCapability(True)
    manlansw.setUnicast(True)
    manlansw.addInterface(manlanif3vc4)
    manlansw.addInterface(manlanif4vc4)
    #manlansw.addInterface(manlanif5vc4)
    manlansw.addInterface(manlanif6vc4)
    manlansw.addInterface(manlanif7vc4)
    
    # 
    # NetherLight
    # 
    
    netherlns   = pynt.xmlns.GetCreateNamespace("http://netherlight.net/#")
    domainNamespaces.append(netherlns)
    netherldev  = pynt.elements.GetCreateDevice("NetherLightDevice", namespace=netherlns)
    netherldev.setName("NetherLight")
    
    # if6: Potential VC-4 (30 free labels) over OC over Lambda over Fiber
    netherl6vc4     = pynt.xmlns.CreateRDFObject("if6-vc4", namespace=netherlns, klass=pynt.elements.PotentialMuxInterface)
    netherl6vc4.setLayer(vc4layer)
    netherl6vc4.setDevice(netherldev)
    #netherl6vc4.setLabel(link6label)
    netherl6vc4.setLabelSet(link6range)
    netherl6oc     = pynt.xmlns.CreateRDFObject("if6-oc", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl6oc.setLayer(oclayer)
    netherl6oc.setDevice(netherldev)
    netherl6lambda = pynt.xmlns.CreateRDFObject("if6-lambda", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl6lambda.setLayer(lambdalayer)
    netherl6lambda.setDevice(netherldev)
    netherl6lambda.setLabel(1310.0)
    netherl6fiber  = pynt.xmlns.CreateRDFObject("if6-fiber", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl6fiber.setLayer(fiberlayer)
    netherl6fiber.setDevice(netherldev)
    netherl6fiber.addClientInterface(netherl6lambda, lambdainfiber)
    netherl6lambda.addClientInterface(netherl6oc, ocinlambda)
    netherl6oc.addClientInterface(netherl6vc4, stsinoc)
    
    # if7: Potential VC-4 (33 free labels) over OC over Lambda over Fiber
    netherl7vc4     = pynt.xmlns.CreateRDFObject("if7-vc4", namespace=netherlns, klass=pynt.elements.PotentialMuxInterface)
    netherl7vc4.setLayer(vc4layer)
    netherl7vc4.setDevice(netherldev)
    #netherl7vc4.setLabel(link7label)
    netherl7vc4.setLabelSet(link7range)
    netherl7oc     = pynt.xmlns.CreateRDFObject("if7-oc", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl7oc.setLayer(oclayer)
    netherl7oc.setDevice(netherldev)
    netherl7lambda = pynt.xmlns.CreateRDFObject("if7-lambda", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl7lambda.setLayer(lambdalayer)
    netherl7lambda.setDevice(netherldev)
    netherl7lambda.setLabel(1310.0)
    netherl7fiber  = pynt.xmlns.CreateRDFObject("if7-fiber", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl7fiber.setLayer(fiberlayer)
    netherl7fiber.setDevice(netherldev)
    netherl7fiber.addClientInterface(netherl7lambda, lambdainfiber)
    netherl7lambda.addClientInterface(netherl7oc, ocinlambda)
    netherl7oc.addClientInterface(netherl7vc4, stsinoc)
    
    # if8 (a): Ethernet over UTP
    # if8 (b): Ethernet over (7-variant) VC-4
    # if8 (c): VC-4 (fixed label: 28)
    netherl8aeth    = pynt.xmlns.CreateRDFObject("if8a-eth", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl8aeth.setLayer(ethlayer)
    netherl8aeth.setDevice(netherldev)
    netherl8autp    = pynt.xmlns.CreateRDFObject("if8a-utp", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl8autp.setLayer(utplayer)
    netherl8autp.setDevice(netherldev)
    netherl8autp.addClientInterface(netherl8aeth, ethinutp)
    
    netherl8beth    = pynt.xmlns.CreateRDFObject("if8b-eth", namespace=netherlns, klass=pynt.elements.StaticInterface)
    netherl8beth.setLayer(ethlayer)
    netherl8beth.setDevice(netherldev)
    netherl8bvc4    = pynt.xmlns.CreateRDFObject("if8b-vc4", namespace=netherlns, klass=pynt.elements.ConfigurableInterface)
    netherl8bvc4.setLayer(vc4layer)
    netherl8bvc4.setDevice(netherldev)
    netherl8bvc4.setLabel(link8label)
    netherl8bvc4.setLabelSet(link8range)
    netherl8bvc4.addClientInterface(netherl8beth, ethin7vc4)
    
    netherl8aeth.addSwitchedInterface(netherl8beth)
    netherl8beth.addSwitchedInterface(netherl8aeth)
    
    netherl8cvc4    = pynt.xmlns.CreateRDFObject("if8c-vc4", namespace=netherlns, klass=pynt.elements.ConfigurableInterface)
    netherl8cvc4.setLayer(vc4layer)
    netherl8cvc4.setDevice(netherldev)
    netherl8cvc4.setLabel(link8label)
    netherl8cvc4.setLabelSet(vc4range)
    
    netherl8bvc4.addLinkedInterface(netherl8cvc4)
    netherl8cvc4.addLinkedInterface(netherl8bvc4)
    
    # VC-4 Switch Matrix, only switching (no swapping)
    netherlsw     = pynt.elements.GetCreateSwitchMatrix("NetherlightSwitchMatrix", namespace=netherlns)
    netherlsw.setLayer(vc4layer)
    netherlsw.setDevice(netherldev)
    netherlsw.setSwitchingCapability(True)
    netherlsw.setSwappingCapability(False)
    netherlsw.setUnicast(True)
    netherlsw.addInterface(netherl6vc4)
    netherlsw.addInterface(netherl7vc4)
    netherlsw.addInterface(netherl8cvc4)
    
    # 
    # Universiteit van Amsterdam
    # 
    
    uvans       = pynt.xmlns.GetCreateNamespace("http://uva.nl/#")
    domainNamespaces.append(uvans)
    uvadev      = pynt.elements.GetCreateDevice("UvADevice", namespace=uvans)
    uvadev.setName("Amsterdam")
    
    # if8: Ethernet over UTP
    uvaif8utp      = pynt.xmlns.CreateRDFObject("if8-utp", namespace=uvans, klass=pynt.elements.StaticInterface)
    uvaif8utp.setLayer(utplayer)
    uvaif8utp.setDevice(uvadev)
    uvaif8eth      = pynt.xmlns.CreateRDFObject("if8-eth", namespace=uvans, klass=pynt.elements.StaticInterface)
    uvaif8eth.setLayer(ethlayer)
    uvaif8eth.setDevice(uvadev)
    uvaif8utp.addClientInterface(uvaif8eth, ethinutp)
    
    # no switch matrix
    
    # 
    # Connections between the domains (Devices)
    # 
    
    # Quebec <--> CA*net
    # if1 <--> if1 (a) (UTP layer)
    uqamif1utp.addLinkedInterface(canetif1autp)
    canetif1autp.addLinkedInterface(uqamif1utp)
    
    # CA*net <--> StarLight
    # if2 <--> if2 (fiber layer)
    canetif2fiber.addLinkedInterface(starlif2fiber)
    starlif2fiber.addLinkedInterface(canetif2fiber)
    
    # StarLight <--> MAN LAN
    # if3 <--> if3 (fiber layer)
    starlif3fiber.addLinkedInterface(manlanif3fiber)
    manlanif3fiber.addLinkedInterface(starlif3fiber)
    
    # CA*net <--> MAN LAN
    # if4 <--> if4 (fiber layer)
    # if5 <--> if5 (fiber layer)
    canetif4fiber.addLinkedInterface(manlanif4fiber)
    manlanif4fiber.addLinkedInterface(canetif4fiber)
    #canetif5fiber.addLinkedInterface(manlanif5fiber)
    #manlanif5fiber.addLinkedInterface(canetif5fiber)
    
    # MAN LAN <--> NetherLight
    # if6 <--> if6 (fiber layer)
    # if7 <--> if7 (fiber layer)
    manlanif6fiber.addLinkedInterface(netherl6fiber)
    netherl6fiber.addLinkedInterface(manlanif6fiber)
    manlanif7fiber.addLinkedInterface(netherl7fiber)
    netherl7fiber.addLinkedInterface(manlanif7fiber)
    
    # NetherLight <--> Amsterdam
    # if8 (a) <--> if8 (UTP layer)
    netherl8autp.addLinkedInterface(uvaif8utp)
    uvaif8utp.addLinkedInterface(netherl8autp)
    
    return domainNamespaces

def WriteToFiles(domains, outputdir="."):
    myout = pynt.output.debug.DebugOutput(os.path.join(outputdir,'glifdemo.txt'))
    myout.output()
    myout = pynt.output.manualrdf.RDFOutput(os.path.join(outputdir,'glifdemo.rdf'))
    myout.output()
    myout = pynt.output.rdf.RDFOutput(os.path.join(outputdir,'glifdemo_rdf.rdf'))
    myout.output()
    myout = pynt.output.dot.DeviceGraphOutput(os.path.join(outputdir,'glifdemo.device.dot'))
    myout.output(domains)
    myout = pynt.output.dot.InterfaceGraphOutput(os.path.join(outputdir,'glifdemo.interface.dot'))
    myout.output(domains)

if __name__=="__main__":
    Main()
