#!/usr/bin/env python
# encoding: utf-8

# Copyright (c) 2007, Jeroen van der Ham
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of TNO nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import getopt
import socket
from construct import *

global verbose
verbose = False

def ospfdump(ipaddress="127.0.0.1", remoteport="2607", localport="4000", filename="ospfdump.log"):
    dumpfile = openDumpFile(filename)
    sync = async = None
    try:
        try:
            sync, async = connectToOspf(ipaddress, remoteport, localport)
            sendSyncMessage(sync)
            recvMessages(async, dumpfile)
        except socket.timeout:
            print "All done!"
    finally:
        if sync: sync.close()
        if async: async.close()
        dumpfile.close()
    
def openDumpFile(filename):
    if os.path.isfile(filename):
       arg = raw_input("%s already exists. Do you wish to continue? [Y/N]: "% filename).strip()
       if arg in "yY":
           return file(filename,'wb')
       else:
            sys.exit(0)
    return file(filename,'wb')
    
    
def recvMessages(async, dumpfile):
    ZebraHeaderStruct = Struct("zebra_msg_header",Byte("version"), Byte("msgtype"), UBInt16("msglen"),UBInt32("msgseq"))
    while True:
        if verbose: print "* Awaiting a header"
        hdrStr = async.recv(8)
        if len(hdrStr) != 8:
            print "! Error, expecting header of 8 bytes, got %s bytes" % len(hdr)
            sys.exit(1)
        hdr = ZebraHeaderStruct.parse(hdrStr)
        if hdr.version != 1:
            print "! Received wrong version, misalignment?"
            sys.exit(1)
        # TODO: Figure out where batch send ends and increase sequence then.
        # if hdr.msgseq != mySeq:
        #     print "! Something is getting out of order? mySeq = %d, Got: %d" % (mySeq, hdr.msgseq)
        # mySeq += 1
        if verbose: print "* Preparing to receive body of length %d (type %d)" % (hdr.msglen, hdr.msgtype)
        bodyStr = async.recv(hdr.msglen)
        if len(bodyStr) != hdr.msglen:
            print "! Error, expecting body of length %d, got %d bytes." % (hdr.msglen, len(bodyStr))
        dumpfile.write(hdrStr+bodyStr)


def sendSyncMessage(sync):
    # Body = Typemask for LSAs to receive (2 bytes),origin (1 byte), number of areas (1 byte)
    # Typemask: FFFF is all LSAs, 0200 is only Opaque.
    # Origin: 0 is non-self, 1 is self, 2 is all

    # typemask = '\xff\xff'
    # origin = 2
    # num_areas=0
    # body = struct.pack("2sBB", typemask, origin, num_areas) 
    # 
    # msgtype = 4
    # zebra_ospf_api_version=1
    # msglen = socket.htons(len(body))
    # msgseq = socket.htonl(2)
    # headerfmt = "BBHL"
    # header = struct.pack(headerfmt, zebra_ospf_api_version, msgtype, msglen, msgseq)
    # msg = header+body
    sync.sendall('\x01\x04\x00\x04\x00\x00\x00\x02\xff\xff\x02\x00')
    
def connectToOspf(ipaddress, remoteport, localport):
    # The OSPF API uses two connections:
    # - A synchronous connection which is inititated from the client
    # - An asynchronouse connection, which is initiated from the server
    #   as a response to a connect at portnumber+1
    # Therefore, we first prepare for an incoming connection, and then 
    # connect ourselves.
    try:
        async = socket.socket(socket.AF_INET, socket.SOCK_STREAM )
        async.bind(('',int(localport)+1))
        async.listen(1)
        sync = socket.socket(socket.AF_INET, socket.SOCK_STREAM )
        sync.bind(('',int(localport)))
    except:
        print "Could not bind to localport %s or %s" % (localport, int(localport)+1)
    if verbose: print "* Connecting to OSPF Daemon"
    try:
        sync.connect((ipaddress,int(remoteport)))
    except:
        print "Could not connect to host %s:%s" % (ipaddress, remoteport)
        sys.exit(2)
    if verbose: print "* Waiting for return connection"
    ch,det = async.accept()
    if verbose: print "* All connected!"
    async.close()
    return sync, ch
    


def usage():
    print '''
ospfdump is designed to connect to a Quagga OSPFd with the OSPF API interface 
enabled (use -a when starting ospfd).

By default ospfdump connects to '127.0.0.1' on port '2607', it then syncs with
the OSPF databse and dumps it to 'ospfdump.log'. ospfdump uses local port 
'4000' (and +1) to initiate the connection.
To change this behavior, use the options as below:

\t-f  --file <filename>      Dump to file (default ospfdump.log)
\t-i  --ip <ip address>      Connect to IP address (default 127.0.0.1)
\t-l  --local <port>         Connect from localport (default 4000)
\t-r  --remote <port>        Connect to port (default 2607)
'''


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:], "hvf:i:l:r:t:", ["help", "verbose", "file=", "ip=", "local=", "remote=","timeout="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    # option processing
    filename = "ospfdump.log"
    ipaddress = "127.0.0.1"
    localport = "4000"
    remoteport = "2607"
    global verbose
    verbose = False
    socket.setdefaulttimeout(10)
    for option, value in opts:
        if option in ("-h", "--help"):
            usage()
            sys.exit()
        if option in ("-f", "--file"):
            filename = value
        if option in ("-i", "--ip"):
            ipaddress = value
        if option in ("-l", "--local"):
            localport = value
        if option in ("-r", "--remote"):
            remoteport = value
        if option in ("-v", "--verbose"):
            verbose = True
        if option in ("-t","--timeout"):
            socket.setdefaulttimeout(float(value))
    ospfdump(ipaddress,remoteport,localport,filename)

if __name__ == "__main__":
    sys.exit(main())
