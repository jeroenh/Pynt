# -*- coding: utf-8 -*-
"""Input module based on expect, used to retrieve information from devices using a command line interface (CLI)
The expect module is not thread-safe; don't share a single ExpectInput among multiple threads."""

# builtin modules
import sys
import re
import logging
# semi-standard modules
try:
    import pexpect
except ImportError:
    sys.stderr.write("Module pexpect is not available. It can be downloaded from http://pexpect.sourceforge.net/\n")
    raise
# local modules
import exceptions
import base
import emulate

# Both the telnet and the SSH module are based on pexpect. Alternatively, it is possible to
# base the telnet module on telnetlib, removing the dependency on pexpect. However, since 
# we need pexepect for SSH anyway, this is easier.

# helper functions

def ParseCLILines(lines, skipStartLines=0, lastSkipLineRe=None, skipEndLines=0):
    """Delete first few and last few lines in an array"""
    if skipStartLines > 0:
        if lastSkipLineRe != None:
            # sanity check. Make sure last line to skip matches the given regexp
            if None == re.match(lastSkipLineRe, lines[(skipStartLines-1)]):
                raise exceptions.MalformedIO("Expected '%s' at line %d of result, but found '%s'." % (lastSkipLineRe, skipStartLines, lines[(skipStartLines-1)].strip()))
        if len(lines) < skipStartLines:
            raise exceptions.MalformedIO("Can't skip first %d lines of result %s. It only contains %d lines." % (skipStartLines, repr(lines), len(lines)))
        del lines[0:skipStartLines]
    if skipEndLines > 0:
        if len(lines) < skipEndLines:
            raise exceptions.MalformedIO("Can't skip last %d lines of result %s. It only contains %d lines." % (skipEndLines, repr(lines), len(lines)))
        del lines[-skipEndLines:]
    return lines


class CLILangInput(base.BaseLangInput):
    """Just a few basic CLI routines. The default BaseLangInput is nearly perfect already."""
    
    # LANGUAGE commands
    
    def makeCommand(self, command):
        """Takes a command, and turns it into a string read to send to the device. 
        It may add a line break (I/O specific), or identifier in the command (language-specific).
        Returns a tuple (identifier, commandstring). The identifier may be None
        if there is no way to match input command and output result."""
        return (None, command+"\n") 
    
    def parseMessage(self, resultString):
        """Takes a message, and parses it into a tripley (resultlines, identifier, status)
        The resultline is typically an array of strings, the identifier some thing to match 
        the result to a given command, and the status is unspecified and is language-specific.
        May raise a ParsingError in case the output can't be parsed, but does not 
        raise an exception if the status is unsuccessful."""
        resultLines = resultString.split('\r\n');
        # We must match \r\n since expect emulates a TTY, which always uses \r\n (even if the application actually send \n)
        # Note that the lines still end with \r. Use rstrip() to remove that.
        # resultLines = resultLines[1:-1] # delete empty first and last line (resultString starts and ends with \r\n)
        logger = logging.getLogger("protocols")
        logger.debug("Received %d lines of data, identifier=%s, status=%s" % (len(resultLines), None, True))
        return (resultLines, None, True)
    
    def statusOK(self, status, command):
        """Checks the status. returns True is the status is a succesful, 
        or raises a CommandFailed, possible with additional information if not."""
        status = bool(status)
        if not status:
            raise CommandFailed("Unexpected status '%s' from command '%s'" % (status, command))
        else:
            return True
    


class CLIIOInput(base.BaseIOInput):
    """Abstract CLI input class."""
    terminal        = None # instance of pexpect.spawn object
    quitCmd         = "quit" # command to log out
    timeout         = 30    # default timeout in seconds
    lastcommand     = ""    # last command for debug output only (only correct for SyncInput: the result we're waiting for may be for another command)
    hasecho         = True  # does sending a command returns an echo?
    
    # I/O commands
    
    def __init__(self, hostname, port=None):
        self.hostname = hostname
        if port != None:
            self.port = port
        base.BaseIOInput.__init__(self)
    
    def getTarget(self):
        """Return a human-readable identifier of the I/O object. For example, the hostname of the filename"""
        return self.hostname
    
    def sendcommand(self, string):
        self.writetolog(string, input=True)
        logger = logging.getLogger("protocols")
        logger.debug("Sending command %s" % (repr(string)))
        try:
            self.terminal.sendline(string)
            if self.hasecho:
                # if the command is 'command\n', the echo is 'command\r\n'
                expectstring = string.replace("\n", "\r\n")
                self.terminal.expect(expectstring, timeout=self.timeout)
                echostring = self.terminal.before + expectstring
                self.writetolog(echostring.replace("\r\n", "\n"), output=True)
        except pexpect.TIMEOUT:
            raise exceptions.MalformedIO("No echo response %s in data %s from %s" % (repr(echostring), repr(self.terminal.before), self.hostname))
        self.lastcommand = string.strip()
    
    def readmessage(self, timeout):
        """Reads text from the terminal up to the next delimiter. Does return the string as-is, 
        without checking validity. The result MUST be an UTF-8 encoded string.
        Should raise an TimeOut in case more then timeout seconds have been passed."""
        logger = logging.getLogger("protocols")
        try:
            self.terminal.expect(self.delimiter, timeout=timeout)
            # Store the result in a variable
            resultString = self.terminal.before
        except pexpect.TIMEOUT:
            raise exceptions.MalformedIO("No delimiter %s after in data %s from %s" % (repr(self.delimiter), self.terminal.before, self.hostname))
        instring = resultString + self.delimiter
        self.writetolog(instring.replace("\r\n", "\n"), output=True)
        logger.debug("Received %d bytes of data" % len(resultString))
        return resultString
    
    def connect(self):
        """Extremely simple connect procedure; you should override this"""
        try:
            self.terminal = pexpect.spawn('telnet "%s"' % (self.hostname))
            self.terminal.timeout = int(self.timeout)
        except pexpect.ExceptionPexpect:
            raise exceptions.NetworkException("Problem spawning a new process ('telnet %s %d')" % (self.hostname, self.port))
    
    def disconnect(self):
        if self.terminal:
            try:
                (identifier, quit) = self.makeCommand(self.quitCmd)
                hasecho = self.hasecho
                self.hasecho = False # don't wait for response
                self.sendcommand(quit)
                self.hasecho = hasecho
                self.terminal.expect(pexpect.EOF)
            except pexpect.EOF:
                self.terminal = None
    

    def setDefaultTimeOut(self, timeout = 30):
        self.timeout = int(timeout)
        if self.timeout <= 0:
            self.timeout = 30
        if self.terminal:
            self.terminal.timeout = self.timeout
    


class TelnetInput(CLIIOInput, CLILangInput, base.BaseSyncInput):
    """Telnet input, based on the expect class. This opens a telnet subprocess, and most likely only works for UNIX."""
    port        = 23
    
    # I/O commands
    
    def connect(self):
        try:
            if not self.username:
                raise AttributeError("username is not set for %s. Please call setLoginCredentials() before getSubject()." % self.hostname)
            self.terminal = pexpect.spawn('telnet %s %d' % (self.hostname, self.port))
            self.terminal.timeout = int(self.timeout)
        except pexpect.ExceptionPexpect:
            raise exceptions.NetworkException("Problem spawning a new process ('telnet %s %d')" % (self.hostname, self.port))
    
    def login(self):
        logger = logging.getLogger("protocols")
        try:
            match = self.terminal.expect(['[Ll]ogin:', '[Pp]assword:', self.prompt])
        except pexpect.TIMEOUT:
            raise exceptions.NetworkException("Time-out while connecting to host ('telnet %s %d')" % (self.hostname, self.port))
        if match == 0:  # Login prompt
            try:
                self.terminal.sendline(self.username)
                match = 1+self.terminal.expect(['[Pp]assword:', self.prompt])
            except pexpect.TIMEOUT:
                raise exceptions.MalformedIO("Unexpected time-out while waiting for prompt from %s" % (self.hostname))
        if match == 1:  # Password prompt
            try:
                self.terminal.sendline(self.password)
                match = 1+self.terminal.expect(['Permission denied', self.prompt])
                if match == 1: # permission denied
                    if self.password:
                        raise exceptions.NetworkException("Password failed when connecting to %s@%s" % (self.username, self.hostname))
                    else:
                        raise exceptions.NetworkException("No password given for %s@%s. Unable to connect" % (self.username, self.hostname))
            except pexpect.TIMEOUT, pexpect.EOF:
                raise exceptions.MalformedIO("Unexpected time-out (>%d sec) while authenticating to %s" % (self.timeout, self.hostname))
        if match != 2: # haven't gotten a prompt yet
            try:
                self.terminal.expect(self.prompt)
            except pexpect.TIMEOUT, pexpect.EOF:
                raise exceptions.MalformedIO("Unexpected time-out (>%d sec) while waiting for prompt from %s" % (self.timeout, self.hostname))
                # raise exceptions.MalformedIO("Expected 'permission denied' or prompt, but got: '%s'" % (self.terminal.before))
        logger.debug("Succesfully logged in to %s" % (self.hostname))
    


class SSHInput(CLIIOInput, CLILangInput, base.BaseSyncInput):
    """SSH input, based on the expect class. This opens a ssh subprocess, and most likely only works for UNIX."""
    port        = 22
    
    # I/O commands
    
    def connect(self):
        try:
            if not self.username:
                raise AttributeError("username is not set for %s. Please call setLoginCredentials() before getSubject()." % self.hostname)
            self.terminal = pexpect.spawn('ssh -p %d %s@%s' % (self.port, self.username, self.hostname))
            self.terminal.timeout = int(self.timeout)
        except pexpect.ExceptionPexpect:
            raise exceptions.NetworkException("Problem spawning a new process ('ssh %s@%s')" % (self.username, self.hostname))
    
    def login(self):
        logger = logging.getLogger("protocols")
        try:
            match = self.terminal.expect(['The authenticity of host .* can\'t be established', '[Pp]assword:', self.prompt])
        except pexpect.TIMEOUT:
            raise exceptions.NetworkException("Time-out (>%d sec) while connecting to host ('ssh %s@%s')" % (self.timeout, self.username, self.hostname))
        if match == 0:  # 'The authenticity of host .* can\'t be established'
            try:
                self.terminal.expect('Are you sure you want to continue connecting')
                self.terminal.sendline('yes')
            except pexpect.TIMEOUT, pexpect.EOF:
                raise exceptions.MalformedIO("Authenticity of host %s can't be established. Expected question, but got time-out" % (self.hostname))
            try:
                match = 1+self.terminal.expect(['[Pp]assword:', self.prompt])
            except pexpect.TIMEOUT, pexpect.EOF:
                raise exceptions.MalformedIO("Unexpected time-out (>%d sec) while waiting for prompt from %s" % (self.timeout, self.hostname))
        if match == 1:  # Password prompt
            try:
                self.terminal.sendline(self.password)
                match = 1+self.terminal.expect(['Permission denied', self.prompt])
                if match == 1: # permission denied
                    if self.password:
                        raise exceptions.NetworkException("Password failed when connecting to %s@%s" % (self.username, self.hostname))
                    else:
                        raise exceptions.NetworkException("No password given for %s@%s. Unable to connect" % (self.username, self.hostname))
            except pexpect.TIMEOUT, pexpect.EOF:
                raise exceptions.MalformedIO("Unexpected time-out (>%d sec) while authenticating to %s" % (self.timeout, self.hostname))
        if match != 2: # haven't gotten a prompt yet
            try:
                self.terminal.expect(self.prompt)
            except pexpect.TIMEOUT, pexpect.EOF:
                raise exceptions.MalformedIO("Unexpected time-out (>%d sec) while waiting for prompt from %s" % (self.timeout, self.hostname))
                # raise exceptions.MalformedIO("Expected 'permission denied' or '%s', but got: '%s'" % (self.prompt, self.terminal.before))
        logger.debug("Succesfully logged in to %s" % (self.hostname))
    


class CLIEmulatorInput(emulate.FileIOInput, CLILangInput, base.BaseSyncInput):
    """Emulates a CLI input, but in reality, reads data from a file"""
    pass


