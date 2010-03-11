# -*- coding: utf-8 -*-
"""OspfInput -- OspfInput can connect to a Quagga Ospf API capable host or read from a byte dump and retrieve the full LSA database and create a topology from that."""

# builtin modules
import logging
import sys
import socket
# semi-standard modules
try:
    # Yes, this is not the preferred python notation, it is the preferred notation for that module.
    # And yes, we're going to need to type it a lot if you don't import it this way :(
    from construct import *
except ImportError:
    sys.stderr.write("Module construct is not available. It can be downloaded from http://construct.wikispaces.com/\n")
    raise
# local modules
import exceptions
import base
import ospflsa
import emulate

class OspfNetworkInputException(Exception):
    pass

class OspfFileInputException(Exception):
    pass

class OspfIOInput(base.BaseIOInput):
    def getTarget(self):
        return "ospf"
    
class OspfLangInput(base.BaseLangInput):
    pass

class OspfNetworkInput(OspfIOInput, OspfLangInput, base.BaseSyncInput):
    
    def __init__(self, hostname=None, remoteport=2607, localport=4000):
        self.hostname    = hostname
        self.remoteport  = remoteport
        self.localport   = localport
        self.logger      = logging.getLogger("protocols")
        self.io          = ()
        socket.setdefaulttimeout(10)
        
    def login(self):
        pass
    
    def connect(self):
        # The Ospf API uses two connections:
        # - A synchronous connection which is inititated from the client
        # - An asynchronouse connection, which is initiated from the server
        #   as a response to a connect at portnumber+1
        # Therefore, we first prepare for an incoming connection, and then 
        # connect ourselves.
        try:
            async = socket.socket(socket.AF_INET, socket.SOCK_STREAM )
            async.bind(('',int(self.localport)+1))
            async.listen(1)
            sync = socket.socket(socket.AF_INET, socket.SOCK_STREAM )
            sync.bind(('',int(self.localport)))
        except socket.error:
            raise OspfNetworkInputException("Could not bind to localport %s or %s" % (self.localport, int(self.localport)+1))
        self.logger.debug("* Connecting to Ospf Daemon")
        try:
            sync.connect((self.hostname,int(self.remoteport)))
        except socket.error:
            raise OspfNetworkInputException("Could not connect to host %s:%s" % (self.hostname, self.remoteport))
        self.logger.debug("* Waiting for return connection")
        ch,det = async.accept()
        async.close()
        self.logger.debug("* All connected!")
        self.io = (sync, ch)
    
    def disconnect(self):
        for sock in self.io:
            sock.close()
    
    def getLSAs(self):
        # First we request a synchronisation from the Ospf daemon
        # Typemask: FFFF is all LSAs, 0200 is only Opaque.
        # Origin: 0 is non-self, 1 is self, 2 is all
        # body = struct.pack("2sBB", typemask, origin, num_areas) 
        # header = struct.pack("BBHL", quagga_ospf_api_version=1, msgtype=4, msglen, msgseq=0)
        # 
        # The bytes below is a sync message for api version 1, requesting all LSAs, from all origins, from all areas.
        self.io[0].sendall('\x01\x04\x00\x04\x00\x00\x00\x02\xff\xff\x02\x00')
        try:
            lsas = self.recvMessages(self.io[1])
        finally:
            self.io[0].close()
            self.io[1].close()
        return lsas
        
    def recvMessages(self, io):
        lsas = []
        QuaggaHeaderStruct = Struct("quagga_msg_header",Byte("version"), Byte("msgtype"), UBInt16("msglen"),UBInt32("msgseq"))
        try:
            while True:
                hdrStr = io.recv(8)
                if len(hdrStr) == 0:
                    # We're at the end of the file, time to get out
                    break
                if len(hdrStr) != 8:
                    raise OspfNetworkInputException("! Error, expecting header of 8 bytes, got %s bytes" % len(hdr))
                hdr = QuaggaHeaderStruct.parse(hdrStr)
                if hdr.version != 1:
                    raise OspfNetworkInputException("! Received wrong version, misalignment?")
                self.logger.debug("* Preparing to receive body of length %d (type %d)" % (hdr.msglen, hdr.msgtype))
                bodyStr = io.recv(hdr.msglen)
                if len(bodyStr) != hdr.msglen:
                    raise OspfNetworkInputException( "! Error, expecting body of length %d, got %d bytes." % (hdr.msglen, len(bodyStr)))
                # We're leaving out the Quagga header
                lsas.append(hdrStr+bodyStr)
        except socket.timeout:
            # There's no other way to figure out that the LSA sending is compelete...
            pass
        self.logger.debug("Connection timed out.")
        return [ospflsa.newLSAFromZebra(lsa) for lsa in lsas]    

class OspfEmulatorInput(emulate.FileIOInput, OspfLangInput, base.BaseSyncInput):
    def connect(self):
        self.io = open(self.filename,'rb')
    
    def getLSAs(self):
        """getLSAsFromOspfDump reads from the open file <filename> and retrieves the separate LSAs from
        the file, and returns them as a list. 
        """
        lsas = []
        QuaggaHeaderStruct = Struct("quagga_msg_header",Byte("version"), Byte("msgtype"), UBInt16("msglen"),UBInt32("msgseq"))
        while True:
            hdrStr = self.io.read(8)
            if len(hdrStr) == 0:
                # We're at the end of the file, time to get out
                break    
            if len(hdrStr) != 8:     # QuaggaHeaderStruct is 8 bytes long
                raise OspfFileInputException("expecting header from %s, got %s" % (self.io.name, len(hdrStr)))
            hdr = QuaggaHeaderStruct.parse(hdrStr)
            if hdr.version != 1:
                raise OspfFileInputException("! Received wrong version, misalignment?")
            bodyStr = self.io.read(hdr.msglen)
            if len(bodyStr) != hdr.msglen:
                raise OspfFileInputException("! Error, expecting body of length %d, got %d bytes." % (hdr.msglen, len(bodyStr)))
            self.logger.debug("Received an LSA.")
            lsas.append(hdrStr+bodyStr)
        return [ospflsa.newLSAFromZebra(lsa) for lsa in lsas]    
    

