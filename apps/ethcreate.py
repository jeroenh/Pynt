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
import pynt.output.idc

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

def DefineNetwork():
    # - Earth          1 physical interface: Ethernet
    # - Vogon          4 physical interface: Ethernet, SONET (3x), 1 Switch Matrix (SONET); 1 fixed switchedTo outside matrix (for Ethernet in SONET)
    # - StarLight      2 physical interfaces: SONET/Ethernet, 2 Switch Matrices (SONET and Ethernet)
    # - MANLAN         5 physical interfaces: SONET, 1 Switch Matrix (SONET)
    # - NetherLight    3 physical interface: Ethernet, SONET (2x), 1 Switch Matrix; 1 fixed switchedTo outside matrix (for Ethernet in SONET)
    # - Amsterdam      1 physical interface: Ethernet
    
    #     Ford
    #       | vlan 28                     untagged
    #    Earth ----------------- Vogon ----------------- Golgafrinchan
    #                tagged         |                        |
    #                               |                 tagged |
    #                 tagged        |          tagged        |     vlan 42
    #    Betelgeuse ------------ Haggunenons ----------- Margrathea --- Dolphins
    #        | vlan 42                                       | vlan 42
    #      Zaphod                                           Mice
    #
    
    domainNamespaces = []
    
    # Get all namespaces, layers and adaptations.
    
    ethns       = pynt.xmlns.GetNamespaceByPrefix("ethernet")
    ethlayer    = pynt.xmlns.GetRDFObject("EthernetNetworkElement",  namespace=ethns, klass=pynt.layers.Layer)
    ethineth    = pynt.xmlns.GetRDFObject("Tagged-Ethernet",         namespace=ethns, klass=pynt.layers.AdaptationFunction)
    
    logger = logging.getLogger("network")
    logger.log(25, "Building demo Ethernet network in memory")
    
    ieee8021qrange = pynt.rangeset.RangeSet("0-4095", itemtype=int, interval=1)
    vlan42         = pynt.rangeset.RangeSet("42", itemtype=int, interval=1)
    vlan28         = pynt.rangeset.RangeSet("28", itemtype=int, interval=1)
    vlanno42       = ieee8021qrange - vlan42
    
    exns           = pynt.xmlns.GetCreateNamespace("http://example.net/#")
    
    # 
    # External
    # 
    
    ford    = pynt.xmlns.GetCreateRDFObject("Ford", namespace=exns, klass=pynt.elements.StaticInterface)
    ford.setLayer(ethlayer)
    ford.setLabel(None)
    
    zaphod  = pynt.xmlns.GetCreateRDFObject("Zaphod", namespace=exns, klass=pynt.elements.StaticInterface)
    zaphod.setLayer(ethlayer)
    zaphod.setLabel(None)
    
    dolphins = pynt.xmlns.GetCreateRDFObject("Dolphins", namespace=exns, klass=pynt.elements.StaticInterface)
    dolphins.setLayer(ethlayer)
    dolphins.setLabel(None)
    
    mice    = pynt.xmlns.GetCreateRDFObject("Mice", namespace=exns, klass=pynt.elements.StaticInterface)
    mice.setLayer(ethlayer)
    mice.setLabel(None)
    
    # 
    # Earth:
    # 
    
    earth    = pynt.elements.GetCreateDevice("Earth", namespace=exns)
    
    # ifford: Untagged, VLAN 28
    ifearth_ford   = pynt.xmlns.GetCreateRDFObject("ifearth_ford", namespace=exns, klass=pynt.elements.ConfigurableInterface)
    ifearth_ford.setLayer(ethlayer)
    ifearth_ford.setDevice(earth)
    ifearth_ford.setLabel(28)
    ifearth_ford.setInternalLabelSet(vlan28)
    # ifvogon: Tagged, all VLANs
    ifearth_vogon_tag  = pynt.xmlns.GetCreateRDFObject("ifearth_vogon_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifearth_vogon_tag.setLayer(ethlayer)
    ifearth_vogon_tag.setDevice(earth)
    ifearth_vogon_tag.setLabelSet(vlan28)
    ifearth_vogon_unt  = pynt.xmlns.GetCreateRDFObject("ifearth_vogon_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifearth_vogon_unt.setLayer(ethlayer)
    ifearth_vogon_unt.setDevice(earth)
    ifearth_vogon_unt.setLabel(None)
    ifearth_vogon_unt.addClientInterface(ifearth_vogon_tag, ethineth)
    
    # Ethernet switch matrix
    earthswitch     = pynt.elements.GetCreateSwitchMatrix("EarthSwitch", namespace=exns)
    earthswitch.setLayer(ethlayer)
    earthswitch.setDevice(earth)
    earthswitch.setSwitchingCapability(True)
    earthswitch.setSwappingCapability(False)
    earthswitch.setUnicast(False)
    earthswitch.setBroadcast(True)
    earthswitch.addInterface(ifearth_ford)
    earthswitch.addInterface(ifearth_vogon_tag)
    
    # 
    # Vogon:
    # 
    
    vogon    = pynt.elements.GetCreateDevice("Vogon", namespace=exns)
    
    # ifearth: Tagged, all VLANs
    ifvogon_earth_tag  = pynt.xmlns.GetCreateRDFObject("ifvogon_earth_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifvogon_earth_tag.setLayer(ethlayer)
    ifvogon_earth_tag.setDevice(vogon)
    ifvogon_earth_tag.setLabelSet(ieee8021qrange)
    ifvogon_earth_unt  = pynt.xmlns.GetCreateRDFObject("ifvogon_earth_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifvogon_earth_unt.setLayer(ethlayer)
    ifvogon_earth_unt.setDevice(vogon)
    ifvogon_earth_unt.setLabel(None)
    ifvogon_earth_unt.addClientInterface(ifvogon_earth_tag, ethineth)
    # ifhaggu: Tagged, all VLANs
    ifvogon_haggu_tag  = pynt.xmlns.GetCreateRDFObject("ifvogon_haggu_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifvogon_haggu_tag.setLayer(ethlayer)
    ifvogon_haggu_tag.setDevice(vogon)
    ifvogon_haggu_tag.setLabelSet(ieee8021qrange)
    ifvogon_haggu_unt  = pynt.xmlns.GetCreateRDFObject("ifvogon_haggu_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifvogon_haggu_unt.setLayer(ethlayer)
    ifvogon_haggu_unt.setDevice(vogon)
    ifvogon_haggu_unt.setLabel(None)
    ifvogon_haggu_unt.addClientInterface(ifvogon_haggu_tag, ethineth)
    # ifgolga: Untagged, any VLAN
    ifvogon_golga_unt  = pynt.xmlns.GetCreateRDFObject("ifvogon_golga_unt", namespace=exns, klass=pynt.elements.ConfigurableInterface)
    ifvogon_golga_unt.setLayer(ethlayer)
    ifvogon_golga_unt.setDevice(vogon)
    ifvogon_golga_unt.setLabel(0)
    ifvogon_golga_unt.setLabelSet(None)
    ifvogon_golga_unt.setInternalLabelSet(ieee8021qrange)
    
    # Ethernet switch matrix
    vogonswitch     = pynt.elements.GetCreateSwitchMatrix("VogonSwitch", namespace=exns)
    vogonswitch.setLayer(ethlayer)
    vogonswitch.setDevice(vogon)
    vogonswitch.setSwitchingCapability(True)
    vogonswitch.setSwappingCapability(False)
    vogonswitch.setUnicast(False)
    vogonswitch.setBroadcast(True)
    vogonswitch.addInterface(ifvogon_earth_tag)
    vogonswitch.addInterface(ifvogon_haggu_tag)
    vogonswitch.addInterface(ifvogon_golga_unt)
    
    # 
    # Golgafrinchan:
    # 
    
    golga    = pynt.elements.GetCreateDevice("Golgafrinchan", namespace=exns)
    
    # ifvogon: Untagged, any VLAN
    ifgolga_vogon_unt  = pynt.xmlns.GetCreateRDFObject("ifgolga_vogon_unt", namespace=exns, klass=pynt.elements.ConfigurableInterface)
    ifgolga_vogon_unt.setLayer(ethlayer)
    ifgolga_vogon_unt.setDevice(golga)
    ifgolga_vogon_unt.setLabel(0)
    ifgolga_vogon_unt.setLabelSet(None)
    ifgolga_vogon_unt.setInternalLabelSet(ieee8021qrange)
    # ifmargr: Tagged, all VLANs
    ifgolga_margr_tag  = pynt.xmlns.GetCreateRDFObject("ifgolga_margr_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifgolga_margr_tag.setLayer(ethlayer)
    ifgolga_margr_tag.setDevice(golga)
    ifgolga_margr_tag.setLabelSet(ieee8021qrange)
    ifgolga_margr_unt  = pynt.xmlns.GetCreateRDFObject("ifgolga_margr_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifgolga_margr_unt.setLayer(ethlayer)
    ifgolga_margr_unt.setDevice(golga)
    ifgolga_margr_unt.setLabel(None)
    ifgolga_margr_unt.addClientInterface(ifgolga_margr_tag, ethineth)
    
    # Ethernet switch matrix
    golgaswitch     = pynt.elements.GetCreateSwitchMatrix("GolgafrinchanSwitch", namespace=exns)
    golgaswitch.setLayer(ethlayer)
    golgaswitch.setDevice(golga)
    golgaswitch.setSwitchingCapability(True)
    golgaswitch.setSwappingCapability(False)
    golgaswitch.setUnicast(False)
    golgaswitch.setBroadcast(True)
    golgaswitch.addInterface(ifgolga_vogon_unt)
    golgaswitch.addInterface(ifgolga_margr_tag)
    
    # 
    # Margrathea:
    # 
    
    margrathea    = pynt.elements.GetCreateDevice("Margrathea", namespace=exns)
    
    # ifgolga: Tagged, all VLANs except 42
    ifmargr_golga_tag  = pynt.xmlns.GetCreateRDFObject("ifmargr_golga_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifmargr_golga_tag.setLayer(ethlayer)
    ifmargr_golga_tag.setDevice(margrathea)
    ifmargr_golga_tag.setLabelSet(vlanno42) # TODO: test if (ieee8021qrange) work. Broadcast should remove VLAN 42.
    ifmargr_golga_unt  = pynt.xmlns.GetCreateRDFObject("ifmargr_golga_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifmargr_golga_unt.setLayer(ethlayer)
    ifmargr_golga_unt.setDevice(margrathea)
    ifmargr_golga_unt.setLabel(None)
    ifmargr_golga_unt.addClientInterface(ifmargr_golga_tag, ethineth)
    # ifhaggu: Tagged, all VLANs except 42
    ifmargr_haggu_tag  = pynt.xmlns.GetCreateRDFObject("ifmargr_haggu_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifmargr_haggu_tag.setLayer(ethlayer)
    ifmargr_haggu_tag.setDevice(margrathea)
    ifmargr_haggu_tag.setLabelSet(vlanno42) # TODO: test if (ieee8021qrange) work. Broadcast should remove VLAN 42.
    ifmargr_haggu_unt  = pynt.xmlns.GetCreateRDFObject("ifmargr_haggu_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifmargr_haggu_unt.setLayer(ethlayer)
    ifmargr_haggu_unt.setDevice(margrathea)
    ifmargr_haggu_unt.setLabel(None)
    ifmargr_haggu_unt.addClientInterface(ifmargr_haggu_tag, ethineth)
    # ifdolphins: Untagged, VLAN 42
    ifmargr_dolphins   = pynt.xmlns.GetCreateRDFObject("ifmargr_dolphins", namespace=exns, klass=pynt.elements.StaticInterface)
    ifmargr_dolphins.setLayer(ethlayer)
    ifmargr_dolphins.setDevice(margrathea)
    ifmargr_dolphins.setLabel(None)
    ifmargr_dolphins.setInternalLabel(42)
    # ifmice: Untagged, VLAN 42
    ifmargr_mice   = pynt.xmlns.GetCreateRDFObject("ifmargr_mice", namespace=exns, klass=pynt.elements.StaticInterface)
    ifmargr_mice.setLayer(ethlayer)
    ifmargr_mice.setDevice(margrathea)
    ifmargr_mice.setLabel(None)
    ifmargr_mice.setInternalLabel(42)
    
    # Ethernet switch matrix
    margrswitch     = pynt.elements.GetCreateSwitchMatrix("MargratheaSwitch", namespace=exns)
    margrswitch.setLayer(ethlayer)
    margrswitch.setDevice(margrathea)
    margrswitch.setSwitchingCapability(True)
    margrswitch.setSwappingCapability(False)
    margrswitch.setUnicast(False)
    margrswitch.setBroadcast(True)
    margrswitch.addInterface(ifmargr_golga_tag)
    margrswitch.addInterface(ifmargr_haggu_tag)
    margrswitch.addInterface(ifmargr_dolphins)
    margrswitch.addInterface(ifmargr_mice)
    
    # 
    # Haggunenons:
    # 
    
    haggunenons    = pynt.elements.GetCreateDevice("Haggunenons", namespace=exns)
    
    # ifmargr: Tagged, all VLANs
    ifhaggu_margr_tag  = pynt.xmlns.GetCreateRDFObject("ifhaggu_margr_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifhaggu_margr_tag.setLayer(ethlayer)
    ifhaggu_margr_tag.setDevice(haggunenons)
    ifhaggu_margr_tag.setLabelSet(ieee8021qrange)
    ifhaggu_margr_unt  = pynt.xmlns.GetCreateRDFObject("ifhaggu_margr_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifhaggu_margr_unt.setLayer(ethlayer)
    ifhaggu_margr_unt.setDevice(haggunenons)
    ifhaggu_margr_unt.setLabel(None)
    ifhaggu_margr_unt.addClientInterface(ifhaggu_margr_tag, ethineth)
    # ifvogon: Tagged, all VLANs
    ifhaggu_vogon_tag  = pynt.xmlns.GetCreateRDFObject("ifhaggu_vogon_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifhaggu_vogon_tag.setLayer(ethlayer)
    ifhaggu_vogon_tag.setDevice(haggunenons)
    ifhaggu_vogon_tag.setLabelSet(ieee8021qrange)
    ifhaggu_vogon_unt  = pynt.xmlns.GetCreateRDFObject("ifhaggu_vogon_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifhaggu_vogon_unt.setLayer(ethlayer)
    ifhaggu_vogon_unt.setDevice(haggunenons)
    ifhaggu_vogon_unt.setLabel(None)
    ifhaggu_vogon_unt.addClientInterface(ifhaggu_vogon_tag, ethineth)
    # ifbetel: Tagged, all VLANs
    ifhaggu_betel_tag  = pynt.xmlns.GetCreateRDFObject("ifhaggu_betel_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifhaggu_betel_tag.setLayer(ethlayer)
    ifhaggu_betel_tag.setDevice(haggunenons)
    ifhaggu_betel_tag.setLabelSet(vlan42)
    ifhaggu_betel_unt  = pynt.xmlns.GetCreateRDFObject("ifhaggu_betel_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifhaggu_betel_unt.setLayer(ethlayer)
    ifhaggu_betel_unt.setDevice(haggunenons)
    ifhaggu_betel_unt.setLabel(None)
    ifhaggu_betel_unt.addClientInterface(ifhaggu_betel_tag, ethineth)
    
    # Ethernet switch matrix
    hagguswitch     = pynt.elements.GetCreateSwitchMatrix("HaggunenonsSwitch", namespace=exns)
    hagguswitch.setLayer(ethlayer)
    hagguswitch.setDevice(haggunenons)
    hagguswitch.setSwitchingCapability(True)
    hagguswitch.setSwappingCapability(False)
    hagguswitch.setUnicast(False)
    hagguswitch.setBroadcast(True)
    hagguswitch.addInterface(ifhaggu_margr_tag)
    hagguswitch.addInterface(ifhaggu_vogon_tag)
    hagguswitch.addInterface(ifhaggu_betel_tag)
    
    # 
    # Betelgeuse:
    # 
    
    betelgeuse    = pynt.elements.GetCreateDevice("Betelgeuse", namespace=exns)
    
    # ifford: Untagged, VLAN 28
    ifbetel_zaphod   = pynt.xmlns.GetCreateRDFObject("ifbetel_zaphod", namespace=exns, klass=pynt.elements.StaticInterface)
    ifbetel_zaphod.setLayer(ethlayer)
    ifbetel_zaphod.setDevice(betelgeuse)
    ifbetel_zaphod.setLabel(None)
    ifbetel_zaphod.setInternalLabel(42)
    # ifhaggu: Tagged, all VLANs
    ifbetel_haggu_tag  = pynt.xmlns.GetCreateRDFObject("ifbetel_haggu_tag", namespace=exns, klass=pynt.elements.PotentialMuxInterface)
    ifbetel_haggu_tag.setLayer(ethlayer)
    ifbetel_haggu_tag.setDevice(betelgeuse)
    ifbetel_haggu_tag.setLabelSet(ieee8021qrange)
    ifbetel_haggu_unt  = pynt.xmlns.GetCreateRDFObject("ifbetel_haggu_unt", namespace=exns, klass=pynt.elements.StaticInterface)
    ifbetel_haggu_unt.setLayer(ethlayer)
    ifbetel_haggu_unt.setDevice(betelgeuse)
    ifbetel_haggu_unt.setLabel(None)
    ifbetel_haggu_unt.addClientInterface(ifbetel_haggu_tag, ethineth)
    
    # Ethernet switch matrix
    betelswitch     = pynt.elements.GetCreateSwitchMatrix("BetelgeuseSwitch", namespace=exns)
    betelswitch.setLayer(ethlayer)
    betelswitch.setDevice(betelgeuse)
    betelswitch.setSwitchingCapability(True)
    betelswitch.setSwappingCapability(False)
    betelswitch.setUnicast(False)
    betelswitch.setBroadcast(True)
    betelswitch.addInterface(ifbetel_zaphod)
    betelswitch.addInterface(ifbetel_haggu_tag)
    
    # 
    # Connections between the domains (Devices)
    # 
    
    # Earth <--> Ford
    ifearth_ford.addLinkedInterface(ford)
    ford.addLinkedInterface(ifearth_ford)
    
    # Earth <--> Vogon
    ifearth_vogon_unt.addLinkedInterface(ifvogon_earth_unt)
    ifvogon_earth_unt.addLinkedInterface(ifearth_vogon_unt)
    
    # Vogon <--> Haggunenons
    ifvogon_haggu_unt.addLinkedInterface(ifhaggu_vogon_unt)
    ifhaggu_vogon_unt.addLinkedInterface(ifvogon_haggu_unt)
    
    # Vogon <--> Golgafrinchan
    ifvogon_golga_unt.addLinkedInterface(ifgolga_vogon_unt)
    ifgolga_vogon_unt.addLinkedInterface(ifvogon_golga_unt)
    
    # Golgafrinchan <--> Margrathea
    ifgolga_margr_unt.addLinkedInterface(ifmargr_golga_unt)
    ifmargr_golga_unt.addLinkedInterface(ifgolga_margr_unt)
    
    # Margrathea <--> Dolphins
    ifmargr_dolphins.addLinkedInterface(dolphins)
    dolphins.addLinkedInterface(ifmargr_dolphins)
    
    # Margrathea <--> Mice
    ifmargr_mice.addLinkedInterface(mice)
    mice.addLinkedInterface(ifmargr_mice)
    
    # Haggunenons <--> Margrathea
    ifhaggu_margr_unt.addLinkedInterface(ifmargr_haggu_unt)
    ifmargr_haggu_unt.addLinkedInterface(ifhaggu_margr_unt)
    
    # Betelgeuse <--> Haggunenons
    ifbetel_haggu_unt.addLinkedInterface(ifhaggu_betel_unt)
    ifhaggu_betel_unt.addLinkedInterface(ifbetel_haggu_unt)
    
    # Betelgeuse <--> Zaphod
    ifbetel_zaphod.addLinkedInterface(zaphod)
    zaphod.addLinkedInterface(ifbetel_zaphod)
    
    return [exns]

def WriteToFiles(domains, outputdir="."):
    myout = pynt.output.debug.DebugOutput(os.path.join(outputdir,'ethernetdemo.txt'))
    myout.output()
    myout = pynt.output.manualrdf.RDFOutput(os.path.join(outputdir,'ethernetdemo.rdf'))
    myout.output()
    #myout = pynt.output.rdf.RDFOutput(os.path.join(outputdir,'glifdemo_rdf.rdf'))
    #myout.output()
    myout = pynt.output.dot.DeviceGraphOutput(os.path.join(outputdir,'ethernetdemo.device.dot'))
    myout.output(domains)
    myout = pynt.output.dot.InterfaceGraphOutput(os.path.join(outputdir,'ethernetdemo.interfaces.dot'))
    myout.output(domains)
    myout = pynt.output.idc.IDCTopoOutput(os.path.join(outputdir,'ethernetdemo.idc.xml'))
    myout.output(domains)
    
if __name__=="__main__":
    Main()
