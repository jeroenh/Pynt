#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Helper class for OSPF parsing.

This module contains code for parsing LSAs from bytes using the construct library.
"""

from construct import *
import logging

class IpAddressAdapter(Adapter):
     def _encode(self, obj, context):
         return "".join(chr(int(b)) for b in obj.split("."))
     def _decode(self, obj, context):
         return ".".join(str(ord(b)) for b in obj)

def IpAddress(name):
    return IpAddressAdapter(Bytes(name, 4))

class ASMetricAdapter(Adapter):
    def _encode(self, obj, context):
        return chr(obj>>16) + chr(obj>>8) + chr(obj)
    def _decode(self, obj, context):
        return ord(obj[0])<<16|ord(obj[1])<<8|ord(obj[2])

def ASMetric(name):
    return ASMetricAdapter(Bytes(name,3))

global ZebraHeaderStruct, ZebraChangeHeader, ZebraHeaderLength, LsaHeader
ZebraHeaderStruct = Struct("zebra_msg_header",Byte("version"), Byte("msgtype"), UBInt16("msglen"),UBInt32("msgseq"))
ZebraChangeHeader = Struct("zebra_change", IpAddress("ifaddr"), UBInt32("area_id"), Byte("self_originated"), Padding(3))
ZebraHeaderLength = ZebraHeaderStruct.sizeof()+ZebraChangeHeader.sizeof()

LsaHeader = Struct("lsa_header",UBInt16("ls_age"), Byte("options"), Byte("type"),
                   IpAddress("in_addr"), IpAddress("adv_router"), UBInt32("ls_seqnum"),
                   UBInt16("checksum"), UBInt16("length"))

def newLSAFromZebra(lsa):
  if ZebraHeaderStruct.parse(lsa).version != 1:
      raise Exception("Missing Zebra Header.")
  myLsaHeader = LsaHeader.parse(lsa[ZebraHeaderLength:])
  if myLsaHeader.type == 1:
      return RouterLSA(lsa)
  elif myLsaHeader.type == 2:
      return NetworkLSA(lsa)
  elif myLsaHeader.type == 5:
      return ASExternalLSA(lsa)
  elif myLsaHeader.type == 10:
      return OpaqueLSA(lsa)
  else:
      raise Exception("Oops, type %s has not been implemented yet." % myLsaHeader.type)

class LSA(object):
    def __init__(self, lsaByteStr):
        self.byteString = lsaByteStr
        self.parse(lsaByteStr)
    
    def parseHeader(self, headerByteStr):
        #  0                   1                   2                   3 
        #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |            LS age             |    Options    |    LS type    | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                        Link State ID                          | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                     Advertising Router                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                     LS sequence number                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |         LS checksum           |             length            | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        cont = LsaHeader.parse(headerByteStr)
        self.type = cont.type
        self.link_state_id = cont.in_addr
        self.adv_router = cont.adv_router
        self.seq_num = hex(cont.ls_seqnum)
        self.checksum = hex(cont.checksum)
    
    def parseBody(self, bodyByteStr):
        pass
        
    def parse(self, byteStr):
        self.parseHeader(byteStr[ZebraHeaderLength:])
        self.parseBody(byteStr[ZebraHeaderLength+LsaHeader.sizeof():])
    
    def getAdvertisingRouter(self):     return self.adv_router
    def getLinkStateId(self):           return self.link_state_id
    

class NetworkLSA(LSA):
    def __str__(self):
        # LS age: 289
        # Options: 0x2  : *|-|-|-|-|-|E|*
        # LS Flags: 0x6  
        # LS Type: network-LSA
        # Link State ID: 10.254.69.165 (address of Designated Router)
        # Advertising Router: 10.254.5.165
        # LS Seq Number: 80000002
        # Checksum: 0x2dbd
        # Length: 32
        # Network Mask: /19
        #       Attached Router: 10.254.3.38
        #       Attached Router: 10.254.5.165
        result  = "LS Type: network-LSA\n"
        result += "Advertising Router: %s\n" % self.adv_router
        result += "Link State ID: %s (address of Designated Router)\n" % self.dr_interface
        result += "LS Seq Number: %s\n" % self.seq_num
        result += "Checksum: %s\n" % self.checksum
        result += "Network Mask: %s\n" % self.network_mask
        for r in self.attached_routers:
            result += "\tAttached Router: %s\n" % r
        return result
    
    def parseBody(self, bodyByteStr):
        #  0                   1                   2                   3 
        #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |            LS age             |      Options  |      2        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                        Link State ID                          | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                     Advertising Router                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                     LS sequence number                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |         LS checksum           |             length            | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                         Network Mask                          | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                        Attached Router                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                              ...                              |
        NetworkLSAStruct = Struct("network_lsa", IpAddress("network_mask"),
                                  GreedyRepeater(IpAddress("attached_router")))
        cont = NetworkLSAStruct.parse(bodyByteStr)
        self.dr_interface = self.link_state_id
        self.network_mask = cont.network_mask
        self.attached_routers = cont.attached_router
    
    def getNetworkMask(self):       return self.network_mask
    def getAttachedRouters(self):   return self.attached_routers

class RouterLSA(LSA):
    def __str__(self):
        # LS age: 22
        # Options: 0x2  : *|-|-|-|-|-|E|*
        # LS Flags: 0x6
        # Flags: 0x0
        # LS Type: router-LSA
        # Link State ID: 10.254.3.38
        # Advertising Router: 10.254.3.38
        # LS Seq Number: 80000004
        # Checksum: 0x62ef
        # Length: 36
        #  Number of Links: 1
        # 
        
        # TODO: print age, options, Flags
        result  = "LS Type: router-LSA\n"
        result += "Link State ID: %s\n" % self.link_state_id
        result += "Advertising Router: %s\n" % self.adv_router
        result += "LS Seq Number: %s\n" % self.seq_num
        result += "Checksum: %s\n" % self.checksum
        result += " Number of links: %s\n" % self.nr_links
        for l in self.links:
            result += str(l)
        return result
    
    def parseBody(self, bodyByteStr):
        #  0                   1                   2                   3 
        #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |            LS age             |     Options   |       1       | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                        Link State ID                          | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                     Advertising Router                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                     LS sequence number                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |         LS checksum           |             length            | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |    0    |V|E|B|        0      |            # links            | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                          Link ID                              | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                         Link Data                             | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |     Type      |     # TOS     |            metric             | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                              ...                              | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |      TOS      |        0      |          TOS  metric          | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                          Link ID                              | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                         Link Data                             | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                              ...                              | 
        # 
        TOSMetric = Struct("tosmetric", UBInt8("TOS"), Padding(1), UBInt16("metric"))
        LinkDescr = Struct("link_descr", IpAddress("link_id"), IpAddress("link_data"), 
                           Byte("type"), Byte("nrTOS"), UBInt16("metric"), 
                           MetaRepeater(lambda ctx:ctx["nrTOS"], TOSMetric))
        RouterLSAStruct = Struct("router_lsa", BitStruct("router_lsa_header", Padding(5),
                                 Bit("V"), Bit("E"), Bit("B")), Padding(1), UBInt16("nr_links"),
                                 MetaRepeater(lambda ctx:ctx["nr_links"], LinkDescr))
        
        cont = RouterLSAStruct.parse(bodyByteStr)
        self.V = cont.router_lsa_header.V
        self.E = cont.router_lsa_header.E
        self.B = cont.router_lsa_header.B
        self.nr_links = cont.nr_links
        self.links = self.parseLinks(cont.link_descr)

    def parseLinks(self, link_descr):
        return [LsaLink(i) for i in link_descr]

class LsaLink(object):
    def __str__(self):
        #   Link connected to: a Transit Network
        #    (Link ID) Designated Router address: 10.254.69.165
        #    (Link Data) Router Interface address: 10.254.65.82
        #     Number of TOS metrics: 0
        #      TOS 0 Metric: 10
        result  = "  Link connected to: a %s\n" % self.linktype(self.type)
        result += "    %s: %s\n" % (self.linkIdMeaning(self.type), self.link_id)
        result += "    (Link Data) Router Interface address: %s\n" % self.link_data
        result += "    Number of TOS metrics: %s\n" % self.nrTOS
        result += "      TOS 0 Metric: %s\n" % self.metric
        for x in range(self.nrTOS):
            result += "        TOS %s Metric: %s\n" % (self.tos_metrics[x](0), self.tos_metrics[x](1))
        return result

    def __init__(self, linkContainer):
        self.link_id = linkContainer.link_id
        self.link_data = linkContainer.link_data
        self.metric = linkContainer.metric
        self.type = linkContainer.type
        self.metric = linkContainer.metric
        self.nrTOS = linkContainer.nrTOS
        self.metric = linkContainer.metric
        self.tosmetrics = [(x.TOS,x.metric) for x in linkContainer.tosmetric]

    def getLinkId(self):    return self.link_id
    def getLinkData(self):  return self.link_data
    def getType(self):      return self.type
    def getMetric(self):	return self.metric

    def linktype(self, id):
        if   id == 1:      return "Point-to-point connection to another router"
        elif id == 2:      return "Transit network"
        elif id == 3:      return "Stub network"
        elif id == 4:      return "Virtual link"

    def linkIdMeaning(self, id):
        if   id == 1:      return "Neighboring router's Router ID"
        elif id == 2:      return "IP address of Designated Router"
        elif id == 3:      return "IP network/subnet number"
        elif id == 4:      return "Neighboring router's Router ID"
        
class ASExternalLSA(LSA):
    def __str__(self):
        # Routing Bit Set on this LSA
        # LS age: 1263
        # Options: (No TOS-capability, DC)
        # LS Type: AS External Link
        # Link State ID: 10.220.242.0 (External Network Number )
        # Advertising Router: 10.254.7.209
        # LS Seq Number: 80000AE6
        # Checksum: 0xF1AB
        # Length: 36
        # Network Mask: /23
        #       Metric Type: 1 (Comparable directly to link state metric)
        #       TOS: 0 
        #       Metric: 20 
        #       Forward Address: 0.0.0.0
        #       External Route Tag: 2001
        result  = "LS Type: AS External Link\n"
        result += "Link State ID: %s (External Network Number)\n" % self.link_state_id
        result += "Advertising Router: %s\n" % self.adv_router
        result += "LS Seq Number: %s\n" % self.seq_num
        result += "Checksum: %s\n" % self.checksum
        result += "Network Mask: %s\n" % self.network_mask
        if not self.E:
            result += "\tMetric Type: 1 (Comparable directly to link state metric)\n"
        else:
            result += "\tMetric Type: 0\n"
        result += "\tTOS: 0\n"
        result += "\tMetric: %s\n" % self.metric
        result += "\tForward Address: %s\n" % self.forwarding_address
        result += "\tExternal Route Tag: %s\n" % self.external_route_tag
        return result
    
    def parseBody(self, bodyByteStr):
        #  0                   1                   2                   3 
        #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |            LS age             |     Options   |      5        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                        Link State ID                          | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                     Advertising Router                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                     LS sequence number                        | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |         LS checksum           |             length            | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                         Network Mask                          | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |E|     0       |                  metric                       | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                      Forwarding address                       | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                      External Route Tag                       | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |E|    TOS      |                TOS  metric                    | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                      Forwarding address                       | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                      External Route Tag                       | 
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
        # |                              ...                              | 
        ExternalTOSStruct = Struct("external_tos", BitStruct("external_tos_bits", Bit("ET"), BitField("tos",7)), ASMetric("tos_metric"),
                                   IpAddress("tos_forwarding_address"), IpAddress("tos_external_route_tag"))
        ASExternalLSAStruct = Struct("as_external_lsa", IpAddress("network_mask"), 
                            BitStruct("as_external_lsa_header", Bit("E"), Padding(7)), ASMetric("metric"),
                            IpAddress("forwarding_address"), UBInt32("external_route_tag"),
                            OptionalGreedyRepeater(ExternalTOSStruct)
                            )
        cont = ASExternalLSAStruct.parse(bodyByteStr)
        self.network_mask = cont.network_mask
        self.E = cont.as_external_lsa_header.E
        self.metric = cont.metric
        self.forwarding_address = cont.forwarding_address
        self.external_route_tag = cont.external_route_tag
        for x in cont.external_tos:
            # External TOS does not seem to happen a lot in the wild.
            # If you find any LSAs that contain this information, please report it
            # at http://ndl.uva.netherlight.nl/trac/ndl/
            raise Exception("Don't know how to handle external TOS: %s" % x)

class OpaqueLSA(LSA):
    def __str__(self):
        result  = "LS Type: Opaque LSA\n"
        result += "Advertising Router: %s\n" % self.adv_router
        result += "LS Seq Number: %s\n" % self.seq_num
        result += "Checksum: %s\n" % self.checksum
        result += "Opaque Type: %s\n" % self.opaque_type
        result += "Opaque ID: %s\n" % self.opaque_id
        result += "Lenght = %s\n" % self.length
        if self.tlvtype == 1:
            result += "Router Address: %s\n" % self.routerAddress
        elif self.tlvtype == 2:
            for name,value in self.subtlvs.items():
                if isinstance(value, lib.container.ListContainer):
                    value = "["+", ".join(map(str,value))+"]"
                if name == "Link type":
                    if value == 1:   result += "\tLink type: Point-to-Point\n"
                    elif value == 2: result += "\tLink type: Multi-access\n"
                    else:            result += "\tLink type: Unknown (%s)\n" % value
                elif name == "Link Protection Type":
                    if   value == '\x01': result += "\t%s: Extra Traffic\n" % name
                    elif value == '\x02': result += "\t%s: Unprotected\n" % name
                    elif value == '\x04': result += "\t%s: Shared\n" % name
                    elif value == '\x08': result += "\t%s: Dedicated 1:1\n" % name
                    elif value == '\x10': result += "\t%s: Dedicated 1+1\n" % name
                    elif value == '\x20': result += "\t%s: Enhanced\n" % name
                elif name == "ISCD": # Interface Switching Capability Descriptor
                    result += str(value)
                else:
                    result += "\t%s: %s\n" % (name, value)
        else:
            result += "\tTLV: %s, %s\n" % (tlv.type, tlv.length)
        return result
        
    def parseHeader(self, headerByteStr):
        #  0                   1                   2                   3
        #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |            LS age             |     Options   |   9, 10 or 11 |
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |  Opaque Type  |               Opaque ID                       |
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |                      Advertising Router                       |
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |                      LS Sequence Number                       |
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |         LS checksum           |           Length              |
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        OpaqueLsaHeader = Struct("opaque_lsa_header",UBInt16("ls_age"), Byte("options"), Byte("type"),
                           Byte("opaque_type"), Bitwise(BitField("opaque_id", 24)),
                           IpAddress("adv_router"), UBInt32("ls_seqnum"),
                           UBInt16("checksum"), UBInt16("length"))
        cont = OpaqueLsaHeader.parse(headerByteStr)
        self.structHeader = cont
        self.type = cont.type
        self.opaque_type = cont.opaque_type
        self.opaque_id = cont.opaque_id
        self.adv_router = cont.adv_router
        self.seq_num = hex(cont.ls_seqnum)
        self.checksum = hex(cont.checksum)
        self.length = cont.length

    def parseBody(self, bodyByteStr):
        #  0                   1                   2                   3
        #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |                                                               |
        # +                                                               +
        # |                      Opaque Information                       |
        # +                                                               +
        # |                              ...                              |
        #  0                   1                   2                   3
        #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |              Type             |             Length            |
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        # |                            Value...                           |
        # .                                                               .
        # .                                                               .
        # .                                                               .
        # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        logging.getLogger("lsa")
        logging.debug("Parsing %s-%s-%s (%s)" % (self.adv_router, self.opaque_type, self.opaque_id, len(bodyByteStr)))
        tlv = Struct("tlv",UBInt16("type"),UBInt16("length"), 
                        Aligned(MetaField("value", lambda ctx: ctx["length"]))
                    )
        OpaqueInfoStruct = Struct("opaque_info", GreedyRepeater(tlv))
        try:
            cont = OpaqueInfoStruct.parse(bodyByteStr)
        except core.FieldError:
            logging.error("Applying more padding to work around dragon bug.")
            bodyByteStr += (len(bodyByteStr)%4)*"\x00"
            cont = OpaqueInfoStruct.parse(bodyByteStr)
        except core.RangeError:
            logging.error("Applying more padding to work around dragon bug.")
            bodyByteStr += (len(bodyByteStr)%4)*"\x00"
            cont = OpaqueInfoStruct.parse(bodyByteStr)            
        if len(cont.tlv) > 1: logging.critical("LSA contains more than one tlv")
        if cont.tlv[0].type == 1: # Router Address
            self.tlvtype = 1
            self.routerAddress = ".".join(str(ord(b)) for b in cont.tlv[0].value)
        if cont.tlv[0].type == 2: # Link TLV
            self.tlvtype = 2
            self.subtlvs = {}
            for subtlv in OpaqueInfoStruct.parse(cont.tlv[0].value).tlv:
                # logging.debug("Parsing tlv type: %s, length %s" % (subtlv.type, subtlv.length)) 
                if subtlv.type == 1:
                    self.subtlvs["Link type"] = ord(subtlv.value)
                elif subtlv.type == 2:
                    self.subtlvs["Link ID"]                  = ".".join(str(ord(b)) for b in subtlv.value)
                elif subtlv.type == 3:
                    self.subtlvs["Local interface"]          = Struct("foo", GreedyRepeater(IpAddress("local"))).parse(subtlv.value).local
                elif subtlv.type == 4:
                    self.subtlvs["Remote interface"]         = Struct("foo", GreedyRepeater(IpAddress("remote"))).parse(subtlv.value).remote
                elif subtlv.type == 5:
                    self.subtlvs["TE metric"]                = Struct("foo", UBInt32("value")).parse(subtlv.value).value
                elif subtlv.type == 6:
                    self.subtlvs["Capacity"]                 = Struct("foo", BFloat32("value")).parse(subtlv.value).value
                elif subtlv.type == 7:
                    self.subtlvs["Max reservable bandwidth"] = Struct("foo", BFloat32("value")).parse(subtlv.value).value
                elif subtlv.type == 8:
                    self.subtlvs["Unreserved bandwidth"]     = Struct("foo", GreedyRepeater(BFloat32("value"))).parse(subtlv.value).value
                elif subtlv.type == 9:
                    self.subtlvs["Admin group"]              = Struct("foo", UBInt32("value")).parse(subtlv.value).value
                elif subtlv.type == 11:
                    val = Struct("foo", IpAddress("local"), IpAddress("remote")).parse(subtlv.value)
                    self.subtlvs["Link local ID"]    = val.local
                    self.subtlvs["Link remote ID"]   = val.remote
                elif subtlv.type == 14:
                    self.subtlvs["Link protection type"]     = Struct("foo", Byte("value"), Bytes("reserved",3)).parse(subtlv.value)
                elif subtlv.type == 15:
                    self.subtlvs["ISCD"] = ISCD(subtlv)
                elif subtlv.type == 16:
                    self.subtlvs["Shared Risk Link Groups"] = Struct("foo", GreedyRepeater(UBInt32("value"))).parse(subtlv.value).value
                elif subtlv.type == 16400:
                    self.subtlvs["Domain ID"] = Struct("foo", UBInt32("value")).parse(subtlv.value).value
                elif subtlv.type == 16641:
                    self.subtlvs["Lambda"] = Struct("foo", UBInt32("value")).parse(subtlv.value).value
                else:  logging.debug("Found an unknown subtlv: type %s, length: %s" % (subtlv.type, subtlv.length))
        # self.tlvs = cont.tlv

class ISCD(object):
    # Interface Switching Capability Descriptor
    def __init__(self, subtlv):
        self.minbandwidth = None
        self.mtu = None
        self.indication = None
        withSwcapSpec = Struct("foo", UBInt8("swcap"), UBInt8("encoding"), Bytes("reserved", 2),
                            Bytes("bandwidth",32),Bytes("swcapspecific", subtlv.length-(9*4))
                     )
        withoutSwCapSpec =  Struct("foo", UBInt8("swcap"), UBInt8("encoding"), Bytes("reserved", 2),
                                Bytes("bandwidth",32))
        if (subtlv.length-(9*4))>0:
            val = withSwcapSpec.parse(subtlv.value)
        else:
            val = withoutSwCapSpec.parse(subtlv.value)
        # logging.debug("Parsed ISCD, val.swcap = %s " % val.swcap)
        self.swcap = val.swcap
        self.encoding = val.encoding
        self.maxbandwidth = Struct("foo", GreedyRepeater(BFloat32("value"))).parse(val.bandwidth).value
        if val.swcap in [1,2,3,4]:
            valspecific = Struct("foo", BFloat32("minbandwidth"), UBInt16("mtu"), Padding(2)).parse(val.swcapspecific)
            self.minbandwidth = valspecific.minbandwidth
            self.mtu = valspecific.mtu
        elif val.swcap == 100:
            valspecific = Struct("foo", BFloat32("minbandwidth"), UBInt8("indication"), Padding(3))
            self.minbandwidth = valspecific.minbandwidth
            self.indication = valspecific.indication
        if hasattr(val, "swcapspecific"):
            self.swcapspecific = val.swcapspecific
        else:
            self.swcapspecific = None
    
    def __str__(self):
        result = ""
        if self.swcap in [1,2,3,4]: result += "\tSwitching Capability: Packet-Switch Capable-%s\n" % self.swcap
        elif self.swcap == 51:      result += "\tSwitching Capability: Layer-2 Switch Capable\n"
        elif self.swcap == 100:     result += "\tSwitching Capability: Time-Division-Multiplex Capable\n"
        elif self.swcap == 150:     result += "\tSwitching Capability: Lambda-Switch Capable\n"
        elif self.swcap == 200:     result += "\tSwitching Capability: Fiber-Switch Capable\n"
        else:                       result += "\tSwitching Capability: %s\n" % self.swcap
        if self.encoding == 1:   result += "\tEncoding: Packet\n"
        elif self.encoding == 2: result += "\tEncoding: Ethernet\n"
        elif self.encoding == 3: result += "\tEncoding: ANSI/ETSI PDH\n"
        elif self.encoding == 5: result += "\tEncoding: SONET / SDH\n"
        elif self.encoding == 6: result += "\tEncoding: Digital Wrapper\n"
        elif self.encoding == 7: result += "\tEncoding: Lambda\n"
        elif self.encoding == 8: result += "\tEncoding: Fiber\n"
        elif self.encoding == 9: result += "\tEncoding: FiberChannel\n"
        result += "\tMax LSP Bandwidth: %s\n" % ("["+", ".join(map(str,self.maxbandwidth))+"]" )
        if self.minbandwidth:
            result += "\tMin LSP Bandwidth: %s\n" % self.minbandwidth
        if self.mtu:
            result += "\tMaximum MTU: %s\n" % self.mtu
        if self.indication == 0: result += "\tIndication: Standard\n"
        elif self.indication == 1: result += "\tIndication: Arbitrary\n"
        if self.swcapspecific:
            result += "\tSwCapSpecific Data: %s Bytes" % len(self.swcapspecific)
        return result
