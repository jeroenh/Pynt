# -*- coding: utf-8 -*-
"""The protocols package is intended to abstract communication between 
a client and a network device. Supported protocols include command line 
interface (cli: telnet and SSH), transaction language 1 (TL1), and 
OSPF. In addition, all protocols support an emulation mode, where commands 
are read from file instead of an actual network connection. 
SNMP is not yet supported.

The abstraction provided by protocol package is a question-answer 
sequence, with optional autonomous messages. The package is thread safe.

The implementation of each input consists of 3 elements:
- An I/O specific part (telnet, socket, file)
- A language specific part (CLI, TL1, OSPF, SNMP)
- An interface specific part (Synchronous or Asynchronous)."""

# local modules
import exceptions
import base

