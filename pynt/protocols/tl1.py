# -*- coding: utf-8 -*-
"""Input module based on expect, used to retrieve information from devices using a command line interface (CLI)"""

# builtin modules
import re
import telnetlib
import socket
import logging
import types
import time
# local modules
import exceptions
import base
import emulate


"""
Example usage:

from pynt.protocols.tl1 import SyncTL1Input, AsyncTL1Input, TL1EmulatorInput, ParseSectionBlock

# Create an IO object for synchronous TL1 protocol
hostname = "device.example.net"
io = SyncTL1Input(hostname, port=3082)
# Alternative, use asynchronous (multi-threaded, faster, but has a small change to leave stale processes behind when a crash occurs)
io = AsyncTL1Input(hostname, port=3082)

# optional set properties of TL1 behaviour
io.setDefaultTimeout(10)
io.hasecho = True
# optionally log all TL1 to a file for debugging later
io.setLogFile("path_to_logfile.log"):

# start() calls connect(), login(), and authorize()
io.username = 'johndoe'
io.password = '1234abc'
io.start()

# send a command and wait for a result:
resultlines = io.command("rtrv-cfg-fiber::all:ctag;")
parseResult(resultlines)

# Asynchronous alternative:
io.callbackCommand("rtrv-cfg-fiber::all:ctag;", parseResult)
# parseResult must be a function or method in the form function(resultlines) or function(resultlines, status)

# Set handler for autonomous messages
io.setAutonomousCallback(handleMessage)
# It is possible to set different callback functions based on the type ("auto", "critical", "major" or "minor"):
io.setAutonomousCallback(handleCriticalMessage, "critical")

# stop() calls deauthorize(), disconnect(), and closeLogFile()
io.stop()


def parseResult(resultlines):
    for line in resultlines:
        # line looks like: 
        # "GGN:PORTID=20064,PORTNAME=to 5530-stack #4,PORTDIR=output,PORTHEALTH=good,PORTCAT=nor,PORTPRIV=0x1"
        
        # First turn the line into a dictionary
        parts = line.split(":")
        properties = ParseSectionBlock(parts[1]) 
        # properties now looks like: {PORTID:"10064",IPORTNAME:"from 5530-stack #4",PORTDIR:"input",...}
        
        # store the result or do something useful...

# While writing your parseResult() function, you may want to use an emulator that reads the TL1 that you previously stored in a log file:
logfile = "path_to_logfile.log"
io = TL1EmulatorInput(logfile)
"""


def ParseSectionBlock(block):
    """Convert a TL1 block consisting of multiple sections to a dictionary.

        That is, convert a string 'var1=value,var2=value,var3=value' to a
        dictionary. This will also handle quoted values, although you will need
        to remove the quote characters yourself.
    """
    regex = {}
    regex['name'] = '[a-zA-Z0-9]+'
    regex['safe_char'] = '[^";:,]'
    regex['qsafe_char'] = '[^"]'

    # the value of a parameter will either just be regular characters, ie
    # safe_char or it will be quoted in case we only accepting inside
    # doublequotes (") or escaped doublequotes (\")
    regex['param_value'] = r"""(?:"|\\") %(qsafe_char)s * (?:"|\\") | %(safe_char)s + """ % regex
    regex['param'] = r""" (?: %(name)s ) = (?: %(param_value)s )? """ % regex

    properties = {}
    for m in re.findall(regex['param'], block, re.VERBOSE):
        (name, value) = m.split("=")
        value = re.sub(r'(^\\"|\\"$)', '', value)
        properties[name.lower()] = value

    return properties



class TL1IOInput(base.BaseIOInput):
    """Abstract class. Create an object, log in to a hostname (or filename or URL) and return a device object, 
    or otherwise sets RDF Objects. Prompt must be a string (not a regexp)"""
    terminal        = None  # instance of Telnet object
    hostname        = ""    # hostname to connect to
    port            = 3082  # TL1-RAW port
    hasecho         = False # does sending a command returns an echo?
    
    def __init__(self, hostname, port=None):
        self.hostname = hostname
        if port != None:
            self.port = port
    
    def getTarget(self):
        """Return a human-readable identifier of the I/O object. For example, the hostname of the filename"""
        return self.hostname
    
    def connect(self):
        try:
            self.terminal = telnetlib.Telnet(self.hostname,self.port)
        except socket.error:
            raise exceptions.NetworkException("Problem connecting to host ('telnet %s %d')" % (self.hostname, self.port))
        # Clear input log. The Glimmerglass gives garbage a short while after the connection is established.
        # [62;1"p >        [?4l [?5l [?7h [?8h [1;50r [50;1H [50;0H [4l <--- garbage
        time.sleep(0.01)
        self.writetolog(self.terminal.read_very_eager(), input=True)
    
    def disconnect(self):
        if self.terminal:
            self.terminal.close()
            self.terminal = None
    
    def sendcommand(self, string):
        """writes a command as-is to the I/O. May call writetolog(). 
        If you call sendcommand(), you must also call readmessage() at some point in time, to avoid
        stale results."""
        self.writetolog(string, input=True)
        logger = logging.getLogger("protocols")
        logger.debug("Sending command %s" % (repr(string)))
        #self.acquireIOlock()
        self.terminal.write(string)
        #self.releaseIOlock()
        if self.hasecho:
            expectstring = string[0:5]
            echostring = self.terminal.read_until(expectstring, timeout=self.timeout)
            echostring += self.terminal.read_until("\r\n", timeout=self.timeout)
            if (expectstring not in echostring):
                logger.error("Did not receive echo of command %s, but got %s." % (repr(string), repr(echostring)))
                # raise exceptions.TimeOut("Did not receive echo of command %s, but got %s." % (repr(string), repr(echostring)))
            self.writetolog(echostring.replace("\r\n", "\n"), output=True)
    
    def readmessage(self, timeout):
        """Reads text from the terminal up to the next terminator. Does return the string as-is, 
        without checking validity. May call writetolog()."""
        logger = logging.getLogger("protocols")
        endtime = time.time() + timeout
        #self.acquireIOlock()
        resultString = self.terminal.read_until(self.terminator, timeout=timeout+1);
        if self.terminator not in resultString:
            logger.error("Did not receive termination string %s in TL1 result %s." % (repr(self.terminator), repr(resultString)))
            raise exceptions.TimeOut("Did not receive termination string %s in %d seconds in TL1 result %s." % (repr(self.terminator), timeout+1, repr(resultString)))
        #self.releaseIOlock()
        if len(resultString) > 0:
            self.writetolog(resultString, output=True)
        if not resultString.endswith(self.terminator):
            if len(resultString) > 0:
                logger.debug("Could not find terminator %s in data %s" % (repr(self.terminator), repr(resultString)))
            raise exceptions.TimeOut("no response %s in %s from %s in %d seconds (timeout=%d sec)." % (repr(self.terminator), repr(resultString), self.hostname, time.time()-endtime+timeout, timeout));
        logger.debug("Received %d bytes of data" % len(resultString))
        return resultString



class TL1LanguageInput(base.BaseLangInput):
    """LanguageInput class part, which is knownledge about the format of TL1 input and 
    output messages, as well as autonomous messages. Automatically sets a unique ctag."""
    ctag            = 1     # identifier to track commands
    terminator      = "\r\n;"
    prompt          = ""
    delimiter       = "\r\n;"
    ignorecase      = True # false = case sensitive; true = case insensitive: makes all commands uppercase.
    
    def authorize(self):
        command = "act-user::%s:ctag::%s;" % (self.username, self.password)
        try:
            resultlines = self.send_and_receive(command, self.timeout)
        except exceptions.CommandFailed:
            # disconnect, but not logout: handled upstream
            # self.disconnect()
            raise exceptions.NetworkException("Password failed when connecting to %s@%s" % (self.username, self.hostname))
    
    def deauthorize(self):
        try:
            self.send_and_receive("canc-user::%s:ctag;" % (self.username), self.timeout)
        except exceptions.MalformedIO:
            # We are actually not checking that the logout worked, but we
            # do not really care given at this point we are not going to
            # do anything any longer with this connection
            pass
    
    def setPrompt(self, prompt):
        if prompt:
            self.prompt = "\r\n" + prompt
        else:
            self.prompt = ""
        self.delimiter = self.terminator + self.prompt
        logger = logging.getLogger("protocols")
        logger.debug("Set delimiter to %s" % repr(self.delimiter))
    
    def statusOK(self, status, command=""):
        """Checks the status. returns True is the status is a succesful, 
        or raises a CommandFailed, possible with additional information if not.
        """
        # status = [responsetype, status, comments]
        if status[1] != "COMPLD":
            raise exceptions.CommandFailed("Commmand %s failed: status=%s, reason: %s" % (command, status[1], status[2]))
    
    def makeCommand(self, command):
        """Takes a command, and turns it into a string read to send to the device. 
        It may add a line break (I/O specific), or identifier in the command (language-specific).
        Returns a tuple (identifier, commandstring). The identifier is the ctag."""
        self.acquireMemLock()
        ctag = self.ctag
        self.ctag += 1
        self.releaseMemLock()
        if (len(command) > 0) and (command[-1] == ";"):
            command = command[:-1]
        command = command.split(":")
        if self.ignorecase:
            command[0] = command[0].upper()
        try:
            command[3] = str(ctag)     # set ctag to empty
            command = ":".join(command)+";"
        except IndexError:
            raise exceptions.MalformedIO("Invalid TL1 command given. The fourth (ctag) parameter MUST be present. E.g.: ACT-USER:::ctag;")
            command = ":".join(command)+";"
        return (str(ctag), command+"\n")
    
    def parseMessage(self, resultString):
        """Takes a message, and parses it into a tripley (resultlines, identifier, status)
        The resultline is an array of result line (e.g. 
        ['10.1a.3:NOP,NONE,NONE:INOPTDEGR=-15.00,INOPTCRIT=-18.0']), the identifier is the 
        ctag. The status is a 3-item list [type, status, comment] with type 'M' or 'A',
        status "DENY" or "COMPLD", and comment whatever string was found between /* and */.
        May raise a ParsingError in case the output can't be parsed, but does not 
        raise an exception if the status is unsuccessful."""
        logger = logging.getLogger("protocols")
        
        # The result should start with a header line (2,3,4), and result lines (5,6):
        #                                                           1
        #    BeautyCees 07-03-13 14:52:28                           2
        # M  123 COMPLD                         (normal response)   3
        # A  123 REPT DBCHG EVT SECU IDVN       (automatic message) 3
        # *C  123 REPT ALM CRS                  (critical alarm)    3
        # **  123 REPT ALM ENV DBCHG EVT SECU   (major alarm)       3
        # *^  123 REPT ALM                      (minor alarm)       3
        #     PLNA                              (error code)        4
        #    /* Here is a comment. */                               5
        #    "10.3a.1-10.3a.2:SRCPORT=10.3a.1,DSTPORT=10.3a.2"      6
        #    "10.2a.7-10.3a.5:SRCPORT=10.2a.7,DSTPORT=10.3a.5"      6
        # return lines formated as:
        #     "resultstring, possible with \"quotes\"" (line type 5)
        # note that the header lines (1,2,3) can be repeated in the list of resultsline (type 5)
        
        identifierRE = re.compile(r'^\s+(\w+) (\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)$');
        statusRE     = re.compile(r'^([MA\*][\*C\^]?)\s+(\S+)\s([\w ]+)$');
        moreStatusRE = re.compile(r'^\s+([\w ]+)$');
        commentRE    = re.compile(r'^\s+/\*(.*)\*/');
        resultRE     = re.compile(r'^\s+"{0,1}([^\n]*)[,"]$');
        
        resultLines = resultString.split('\r\n');
        
        commentlines = []
        resultlines  = []
        responsetype = None
        status = None;
        ctag   = None;
        skiplines = True  # only store result and comment lines after a valid status line
        
        # line types
        for line in resultLines:
            statusmatch = statusRE.match(line)
            morestatusmatch = moreStatusRE.match(line)
            identifiermatch = identifierRE.match(line)
            commentmatch = commentRE.match(line)
            resultmatch = resultRE.match(line)
            if statusmatch:
                if ctag == None:
                    responsetype = statusmatch.group(1)
                    ctag   = statusmatch.group(2)
                    status = statusmatch.group(3) # warning: may be more then one word! (e.g. "COMPLD" or "DENY" or "REPT ALM CRS")
                    skiplines = False
                elif ctag == statusmatch.group(2):
                    skiplines = False
                else:
                    logger.warning("Ignoring TL1 output with ctag %s, since the output of ctag %s is not finished (we can only handle output one-by-one)." % (statusmatch.group(2), ctag))
                    skiplines = True
            elif morestatusmatch:
                status = status + " " + morestatusmatch.group(1) # warning: may be more then one word!
            elif resultmatch:
                match = resultmatch.group(1)
                if skiplines:
                    if ctag == None:
                        logger.error("Haven't receive a valid status line yet. Thus skip TL1 result line %s" % repr(match))
                    else:
                        logger.warning("Skip TL1 result line %s" % repr(match))
                else:
                    resultlines.append(match)
            elif commentmatch:
                match = commentmatch.group(1)
                if skiplines:
                    logger.warning("Skip TL1 comment line %s" % repr(match))
                else:
                    commentlines.append(match.strip())
            elif identifiermatch:
                pass
            elif line == "":  # this instruction must come before the line[0] == ">" checks
                pass
            elif line[0] == ">":
                pass
            elif line[0] == "<":
                pass
            elif line == ";":
                skiplines = True # termination line
            else:
                logger.error("Skip uknown TL1 line %s" % repr(line))
        if ctag == None:
            raise exceptions.MalformedIO("Could not find valid response header (e.g. 'M  123 COMPLD') in response %s" % repr(resultString))
            # NOTE: we actually like to include the associated command that was send out, but we don't have that information.
            # However, experience showed that command is often unrelated to the alarm. So we leave it as it is.
        comment = " ".join(commentlines) # paste them together
        # The comment line typically contains the error message
        status = [responsetype, status, comment]
        logger.debug("Received %d lines of data, identifier=%s, status=%s" % (len(resultlines), ctag, status))
        return (resultlines, ctag, status)
    
    def isAutonomousType(self, identifier, status):
        """Given the identifier and status, decide if the message is autonomous,
        and if so, if it is of a certain type. For regular (non-autonomous), return None."""
        responsetype = status[0]
        # (responsetype, status, comment) = status
        if responsetype == 'M':
            return False     # regular message
        elif (responsetype[0] == "A"):
            return "auto";     # autonomous message or no alarm
        elif (responsetype == "*C"):
            return "critical";     # critical alarm
        elif (responsetype == "**"):
            return "major";     # major alarm
        elif (responsetype == "*^"):
            return "minor";     # minor alarm
        else:
            raise exceptions.MalformedIO("Received an unknown message type '%s' (only understand M, A and *) with identifier %s from %s" % (responsetype, identifier, self.getTarget()))



# Note: first parent takes precedence over other parent classes. 
class SyncTL1Input(TL1IOInput, TL1LanguageInput, base.BaseSyncInput):
    pass



# Note: first parent takes precedence over other parent classes. 
class AsyncTL1Input(TL1IOInput, TL1LanguageInput, base.BaseAsyncInput):
    pass



class TL1EmulatorInput(emulate.FileIOInput, TL1LanguageInput, base.BaseSyncInput):
    """Emulates a TL1 input, but in reality, reads data from a file.
    This class overrides the regular makeCommand() and parseMessage() methods
    and always sets the ctag to an empty string."""
    ignorecredentials   = True # if true, sets username and password to none for act-user and canc-user
    def makeCommand(self, command):
        """TL1 emulation: removes the ctag. The identifier is None"""
        if command[-1] == ";":
            command = command[:-1]
        command = command.split(":")
        try:
            command[3] = ""     # set ctag to empty
        except IndexError:
            raise exceptions.MalformedIO("Invalid TL1 command given. The fourth (ctag) parameter MUST be present. E.g.: ACT-USER:::ctag;")
        if self.ignorecase:
            command[0] = command[0].upper()
        if self.ignorecredentials and (command[0] in ["ACT-USER", "CANC-USER"]):
            # e.g. "act-user::username:ctag::password"
            # if len(command) > 2:
            #     command[2] = ""     # remove username
            if len(command) > 5:
                command[5] = ""     # remove password
        command = ":".join(command)+";"
        return (None, command+"\n")
    
    def parseMessage(self, resultString):
        (responselines, ctag, status) = TL1LanguageInput.parseMessage(self, resultString)
        return (responselines, None, status)
    


