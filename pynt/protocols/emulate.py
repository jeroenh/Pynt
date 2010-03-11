# -*- coding: utf-8 -*-
"""Input module based on emulation of command-reponses. The commands and responses are read from a file, and returned as-is.
I originally called this module 'file', but that lead to name clashes with the internal function file."""

# builtin modules
import re
import logging
# local modules
import exceptions
import base

class FileIOInput(base.BaseIOInput):
    """Takes a file, and reads the commands."""
    filename        = ""
    commands        = None  # dict of {command: response}. must be set in __init__
    responses       = None  # array of outstanding responses. A response is added after sending a command.
    
    # I/O commands
    
    def __init__(self, filename):
        self.filename = filename
        base.BaseIOInput.__init__(self)
        self.commands  = {}
        self.responses = []
        self.logger = logging.getLogger("protocols")
    
    def getTarget(self):
        """Return a human-readable identifier of the I/O object. For example, the hostname of the filename"""
        return self.filename
    
    def connect(self):
        """Read log file, and parses it. Store the command, result pairs in self.commands"""
        try:
            io = file(self.filename, 'r')
        except (IOError, OSError):
            raise exceptions.NetworkException("Problem opening to file %s" % (self.filename))
        contents = io.read()
        io.close()
        # Emulate a TTY: all line delimeters are \r\n.
        # ugly, but fast: replace \n with \r\n, only if the 'n wasn't already part of \r\n
        contents = contents.replace("\n", "\r\n").replace("\r\r\n", "\r\n")
        delimiter = re.compile(self.delimiter)
        contents = delimiter.split(contents)
        # The first match may be a simple prompt, as opposed to be a delimiter.
        # TODO: handle empty prompt
        promptdelimiter = re.compile(self.prompt)
        firstmatch = promptdelimiter.split(contents[0], 1)  # maxsplit=1
        if len(firstmatch) > 1:
            #self.logger.debug("deleting first part %s" % (repr(firstmatch[0])))
            contents[0] = firstmatch[1] # remove everything before first prompt
        else:
            #self.logger.debug("no %s in first part; deleting %s" % (repr(self.prompt), contents[0]))
            del contents[0] # remove everything before first delimiter/prompt
        lastmatch = contents[-1].split(self.terminator, 1)  # maxsplit=1
        if len(lastmatch) > 1:
            #self.logger.debug("deleting last part %s" % (repr(lastmatch[1])))
            contents[-1] = lastmatch[0]
        else:
            #self.logger.debug("no %s in last part; deleting %s" % (repr(self.terminator), repr(contents[-1])))
            del contents[-1]
        for commandresponse in contents:
            commandresponse = commandresponse.split("\r\n", 1) # maxsplit = 1
            command = commandresponse[0].strip()
            if len(command) == 0:
                continue
            (identifier, command) = self.makeCommand(command)
            command = command.strip()
            # Note: previous code returned "False" as identifier in case command string could not be parsed.
            # That is bad practice.
            assert(identifier != False)  # makeCommand should simply raise an exception, instead of passing False in the identifier.
            #if identifier == False:  # False means the command is invalid; None means all is well, but there is no identifier.
            #    self.logger.debug("skip command '%s': invalid format" % (command))
            #    continue
            # TODO: remove 6 lines of obsolete code and comments above.
            if len(commandresponse) == 2:
                response = commandresponse[1]
            else:
                response = ""
            self.logger.debug("caching command '%s': %d bytes" % (command, len(response)))
            self.commands[command] = response
        self.logger.debug("cached %d commands" % len(self.commands))
    
    def disconnect(self):
        # must be overriden, even if it does nothing.
        self.commands = {}
    
    def sendcommand(self, string):
        # IF SYNCHRONOUS
        if len(self.responses) > 0:
            raise exceptions.NetworkException("Can't send another command as long as response of previous command is not read")
        # END IF
        self.writetolog(string, input=True)
        self.logger.debug("Sending command %s" % (repr(string)))
        string = string.strip()
        if string in self.commands:
            self.acquireMemLock()
            self.responses.append(self.commands[string])
            self.releaseMemLock()
        else:
            raise exceptions.NetworkException("Command '%s' not found in log file %s." % (string, self.filename))
    
    def readmessage(self, timeout):
        """Returns """
        # IF SYNCHRONOUS
        if len(self.responses) == 0:
            raise exceptions.NetworkException("Can't retrieve response, since no command was send")
        # ELSE
        # wait till len(self.responses) > 0. not implemented here.
        # END IF
        self.acquireMemLock()
        # "Pop" from the beginning of the responses array
        result = self.responses[0]
        del self.responses[0]
        self.releaseMemLock()
        self.writetolog(result, output=True)
        self.logger.debug("Received %d bytes of data" % len(result))
        return result
    
    def setDefaultTimeOut(self, timeout = 30):
        # need to override, simply because the base class sets self.terminal.timeout.
        self.timeout = int(timeout)
        if self.timeout <= 0:
            self.timeout = 30

