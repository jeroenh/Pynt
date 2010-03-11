# -*- coding: utf-8 -*-
"""Internal module of protocols with abstract base classes. 
Applications should not directly import this module, expect to make subclasses.
As a reminder: all internal strings, like identifier, should be 
represented in UTF-8. Use pynt.xmlns.UTF8 if you need help converting."""

# builtin modules
import types
import logging
import time
import threading    # for AsyncInput
# import traceback
# local modules
import exceptions

class BaseIOInput(object):
    """Base I/O input. Abstract class, forming a third part of the BaseInput class, along with BaseLangInput and BaseCommandInput"""
    timeout = 30    # default time-out in seconds
    
    # I/O SPECIFIC METHODS
    
    def __init__(self):
        """Prepares the actual underlying I/O, given the parameters given at initialization.
        (e.g. hostname, port, filename, url, File object). If possible, delays the actual
        opening of the I/O till connect() is called, so that setLoginCredentials() can be 
        called in the mean time."""
        pass
    
    def getTarget(self):
        """Return a human-readable identifier of the I/O object. For example, the hostname of the filename"""
        return "baseIO"
    
    def connect(self):
        """Opens the actual I/O connection to file or device. This is called, just before login() and authorize()"""
        pass
    
    def disconnect(self):
        """closes the I/O connection. You shouldn't call it more than once. Sets the actually I/O object to None, if any"""
        pass
    
    def setDefaultTimeout(self, timeout):
        self.timeout = int(timeout)
    
    def login(self):
        """Login to a terminal, using I/O specific (rather than language-specific) routines. 
        Uses the username and password of the BaseLanguageInput"""
        pass
    
    def sendcommand(self, string):
        """writes a command as-is to the I/O. 
        If you call sendcommand(), you must also call readmessage() at some point in time, to avoid
        stale results."""
        raise NotImplementedError("BaseIOInput.sendcommand() is an abstract method. please override in %s" % type(self).__name__)
        self.writetolog(string, input=True)
        logger = logging.getLogger("protocols")
        logger.debug("Sending command %s" % (repr(string)))
    
    def readmessage(self, timeout):
        """Reads text from the terminal up to the next delimiter. Does return the string as-is, 
        without checking validity. The result MUST be an UTF-8 encoded string.
        Should raise an TimeOut in case more then timeout seconds have been passed."""
        raise NotImplementedError("BaseIOInput.readmessage() is an abstract method. please override in %s" % type(self).__name__)
        resultString = ""
        self.writetolog(resultString, output=True)
        logger = logging.getLogger("protocols")
        logger.debug("Received %d bytes of data" % len(resultString))
        return resultString



class BaseLangInput(object):
    """Base Language input. Abstract method, forming a third part of the BaseInput class, along with BaseIOInput and BaseCommandInput"""
    username    = ""
    password    = ""
    terminator  = "\r\n"    # string that signifies the end of a response message
    prompt      = ">"       # string that signifies the start of an input message
    delimiter   = "\r\n>"   # the delimiter := terminator + prompt
    # The distinction is only relevant when waiting for the first prompt or the last terminator before the EOF.
    # For most languages, the prompt may be a regular expression (though this is not a requirement)
    logfile     = None
    
    # LANGUAGE SPECIFIC METHODS
    
    def authorize(self):
        """Authorize with a command, using language specific (rather than I/O-specific) routines.
        May call send_and_receive(), but NOT command(), since that may be threaded."""
        pass
    
    def deauthorize(self):
        """Deauthorize, prior to disconnecting.
        May call send_and_receive(), but NOT command(), since that may be threaded."""
        pass
    
    def setPrompt(self, prompt):
        self.prompt = prompt
        self.delimiter = self.terminator + self.prompt
        logger = logging.getLogger("protocols")
        logger.debug("Set delimiter to %s" % repr(self.delimiter))
    
    def statusOK(self, status, command):
        """Checks the status. returns True is the status is a succesful, 
        or raises a CommandFailed, possible with additional information."""
        status = bool(status)
        if not status:
            raise CommandFailed("Unexpected status '%s' from command '%s'" % (status, command))
    
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
        resultLines = resultString.split('\n');
        return (resultLines, None, True)
    
    def isAutonomousType(self, identifier, status):
        """Given the identifier and status, decide if the message is autonomous,
        and if so, if it is of a certain type. For regular (non-autonomous), return False."""
        return False
    
    def setLoginCredentials(self, username, password):
        """set login credentials. Set password to "" if no password is required.
        The username are used both for login (e.g. telnet/SSH) and authorize (e.g. TL1).
        This assumes there is not overlap between login and authorize, which is practice always true."""
        self.username       = username
        if password != None:
            self.password   = password
    
    def setLogFile(self, logfile):
        """Set log file to the given path"""
        assert isinstance(logfile, str)
        self.logfile = file(logfile, "a")
    
    def closeLogFile(self):
        if self.logfile:
            self.logfile.close()
            self.logfile = None
    
    def writetolog(self, logstring, input=False, output=False):
        """Write to log file"""
        if self.logfile:
            self.acquireLoglock()
            if input:
                self.logfile.write("\n==input==\n")
            elif output:
                self.logfile.write("\n==output==\n")
            else:
                self.logfile.write("\n==i/o==\n")
            self.logfile.write(logstring)
            self.releaseLoglock()



class BaseSyncInput(object):
    """Base Command input, Synchronous version. 
    Abstract class, forming a third part of the BaseInput class, along with BaseIOInput and BaseLangInput.
    The synchronous version does not create new threads, and will only send one command at a time to the 
    I/O. It will block till a response is returned, and process that one."""
    autocallbacks   = None  # Dictionary with Callback functions for autonomous messages
    
    # COMMAND SPECIFIC METHODS
    
    def getmessage(self, identifier, timeout):
        """Given an identifier, waits till the appropriate message is returned by the device.
        This function is blocking, altough it may give a timeout, if nothing was returned in time.
        Returns tuple (resultlines, status)."""
        endtime = time.time() + timeout
        skipcount = 0
        logger = logging.getLogger("protocols")
        while True:
            result = self.readmessage(timeout)  # may raise a TimeOut
            (resultlines, residentifier, status) = self.parseMessage(result)
            autotype = self.isAutonomousType(residentifier, status)
            if (autotype != False):
                # Autonomous message
                if autotype in self.autocallbacks:
                    callback = self.autocallbacks[autotype]
                    logger.info("Sending autonomous message (type %s, identifier %s) to %s" % (autotype,residentifier,callback.__name__))
                    self.callback(callback, resultlines, status)
                elif True in self.autocallbacks:   # catch-all callback function
                    callback = self.autocallbacks[True]
                    logger.info("Sending autonomous message (type %s, identifier %s) to %s" % (autotype,residentifier,callback.__name__))
                    self.callback(callback, resultlines, status)
                else:
                    logger.warning("Skipping unhandled autonomous message (type %s, identifier %s)" % (autotype,residentifier))
            elif identifier == residentifier:
                logger.debug("Got matching result for identifier %s" % identifier)
                break
            else:
                skipcount += 1
                logger.error("Skipping regular message with identifier %s" % (residentifier))
            if time.time() > endtime:
                raise exceptions.TimeOut("No reply with correct identifier %s after %d seconds (skipped %d responses)" % (identifier, timeout, skipcount))
                resultlines = []
                status = False
                break
        return (resultlines, status)
    
    def send_and_receive(self, command, timeout):
        """Shortcut for makeCommand(), sendcommand(), readmessage(), parseMessage().
        This only works for synchronous I/O. For asynchronous I/O, this function
        is only be used for authorization and de-authorization. Returns a tuple (resultlines, status)."""
        (identifier, string) = self.makeCommand(command)
        self.sendcommand(string)
        (resultlines, status) = self.getmessage(identifier, timeout=timeout)
        self.statusOK(status, command)
        return (resultlines, status)
    
    def command(self, command, timeout=None):
        """The main functons of BaseInput. Takes a command, and returns the result as an array of strings.
        Makes sure the result is a match of the given command, and no error status was raised.
        Language, I/O, and sync/async specific."""
        if timeout == None:
            timeout = self.timeout
        (resultlines, status) = self.send_and_receive(command, timeout)
        self.statusOK(status, command)
        return resultlines
    
    def isCorrectCallback(self, callback):
        """Verifies that the callback function has the proper format: f(lines) or f(lines, status=None).
        Returns a boolean; does not raise an exception on error"""
        if isinstance(callback, types.FunctionType):
            argnames = callback.func_code.co_varnames
            argcount = callback.func_code.co_argcount
            return (argcount in [1,2])
        elif isinstance(callback, types.MethodType):
            argcount = callback.func_code.co_argcount
            return (argcount in [2,3])
        else:
            return False
    
    def hasStatusArgument(self, callback):
        """Verifies that the callback function has the proper format: f(lines) or f(lines, status=None).
        Returns a boolean; does not raise an exception on error"""
        if isinstance(callback, types.FunctionType):
            argcount = callback.func_code.co_argcount
            return (argcount == 2)
        elif isinstance(callback, types.MethodType):
            argcount = callback.func_code.co_argcount
            return (argcount == 3)
        else:
            return False
    
    def callbackCommand(self, command, callback, timeout=None):
        """The main functons of BaseInput. Takes a command, and sends the result to the 
        callback functions. The function returns immediately, and is mostly asynchronous, 
        if possible by the underlying I/O."""
        assert self.isCorrectCallback(callback) 
        # ("Callback function %s has not the proper argument list: %s(resultlines) or %s(resultline, status=None)", (callback.func_name,callback.func_name,callback.func_name))
        if timeout == None:
            timeout = self.timeout
        (resultlines, status) = self.send_and_receive(command, timeout)
        self.statusOK(status, command)
        self.callback(callback, resultlines, status=status)
    
    def callback(self, function, resultlines, status=None):
        """Call function with resultlines as argument. Either in a new thread or simply the current thread."""
        if self.hasStatusArgument(function):
            function(resultlines, status)
        else:
            function(resultlines)
    
    def setAutonomousCallback(self, callback, autotype=True):
        """Set the function which is called for autonomous messages. If type is set, the function is 
        only called when isAutonomousType() in Language parser returns the same string"""
        assert self.isCorrectCallback(callback) 
        # ("Callback function %s has not the proper argument list: %s(resultlines) or %s(resultline, status=None)", (callback.func_name,callback.func_name,callback.func_name))
        if not self.autocallbacks:
            self.autocallbacks = {}
        assert autotype != None
        logger = logging.getLogger("protocols")
        logger.debug("Assigning callback function %s() to callback type %s" % (callback.__name__, autotype))
        self.autocallbacks[autotype] = callback
    
    def start(self):
        """Make sure the actual I/O for the file or device is ready. logs in, authorize.
        You shouldn't call it more than once"""
        logger = logging.getLogger("protocols")
        logger.debug("Fetching information from %s using %s" % (self.getTarget(), type(self).__name__))
        if not self.autocallbacks:
            self.autocallbacks = {}
        self.connect()
        self.login()
        self.authorize()
    
    def stop(self):
        """Deauthorizes, logs out, and closes the I/O connection. You shouldn't call it more than once"""
        self.deauthorize()
        self.disconnect()
        self.closeLogFile()
    
    def acquireMemLock(self):
        return True;
    
    def releaseMemLock(self):
        return True;
    
    def acquireLoglock(self):
        return True;
    
    def releaseLoglock(self):
        return True;



class BaseAsyncInput(BaseSyncInput):
    """Base Command input, Asynchronous version. 
    Abstract class, forming a third part of the BaseInput class, along with BaseIOInput and BaseLangInput.
    The asynchronous version uses two threads: one to send commands, and one to receive them. 
    If command() is used, it is still blocking, but with callbackCommand() multiple commands can be send 
    to a device at the same time. This function is obviously thread-safe. Other Input classes wanting to 
    remain thread safe, should liberously call acquireIOlock() and acquireMemLock(), and release*Lock() of course"""
    messages    = None  # dict (set in createThreads) of identifier: (status, resultlines)
    callbacks   = None  # dict (set in createThreads) of identifier: (callback, timeout). Unset for synchronous messages.
    receivethread = None  # threading.Thread() object. continuously fetches information from the device.
    dorun       = False # signal the receivethread to keep running, or to stop.
    threadedcallback = False    # If True, callbacks are made in a new thread
    callbackthread = None  # dict of Threads
    
    # COMMAND SPECIFIC METHODS
    
    def send_and_receive(self, command, timeout):
        """Shortcut for makeCommand(), sendcommand(), readmessage(), parseMessage().
        This only works for synchronous I/O. For asynchronous I/O, this function
        is only be used for authorization and de-authorization. Returns a tuple (resultlines, status).
        This function is strictly synchronous and does not directly call getmessage(), since that is asynchronous"""
        (cmdidentifier, string) = self.makeCommand(command)
        self.sendcommand(string)
        result = self.readmessage(timeout)  # may raise a TimeOut
        (resultlines, residentifier, status) = self.parseMessage(result)
        self.statusOK(status, command)
        if cmdidentifier != residentifier:
            raise CommandFailed("Result identifier %s does not match command identifier %s for command %s." % (residentifier, cmdidentifier, command))
        return (resultlines, status)

    def command(self, command, timeout=None):
        """The main functons of BaseInput. Takes a command, and returns the result as an array of strings.
        Makes sure the result is a match of the given command, and no error status was raised.
        Language, I/O, and sync/async specific."""
        (identifier, string) = self.makeCommand(command)
        # self.addIdentifierCallback(identifier, None, timeout)
        try:
            self.sendcommand(string)
            if timeout == None:
                timeout = self.timeout
            (resultlines, status) = self.getmessage(identifier, timeout=timeout)
            self.statusOK(status, command)
        except: # all exceptions, including keyboard-interupts
            self.stopThreads(timeout=0)
            raise
        return resultlines
    
    def callbackCommand(self, command, callback, timeout=None):
        """The main functons of BaseInput. Takes a command, and sends the result to the 
        callback functions. The function returns immediately, and is mostly asynchronous, 
        if possible by the underlying I/O."""
        assert self.isCorrectCallback(callback) 
        # ("Callback function %s has not the proper argument list: %s(resultlines) or %s(resultline, status=None)", (callback.func_name,callback.func_name,callback.func_name))
        try:
            (identifier, string) = self.makeCommand(command)
            self.addIdentifierCallback(identifier, callback, timeout)
            self.sendcommand(string)
        except: # all exceptions, including keyboard-interupts
            self.stopThreads(timeout=0)
            raise
    
    def addIdentifierCallback(self, identifier, callback, timeout=None):
        """Adds parameters for the callback to the callbacks variable"""
        if timeout == None:
            timeout = self.timeout
        self.acquireMemLock()
        if identifier in self.callbacks:
            raise NetworkException("A command with identifier %s was already sent. Can't use the same identifier more than once in asynchronous mode." % identifier)
        logger = logging.getLogger("protocols")
        logger.debug("Remember callback function %s() for identifier %s" % (callback.__name__, identifier))
        self.callbacks[identifier] = (callback, time.time()+timeout)
        self.releaseMemLock()
    
    def getmessage(self, identifier, timeout):
        """Given an identifier, waits till the appropriate message shows up in the messages{} dictionary.
        This function is blocking, altough it may give a timeout, if nothing was returned in time.
        Returns tuple (resultlines, status). This function must only be called for async mode. For sync mode, call send_and_receive"""
        if identifier in self.callbacks:
            raise AssertionError("getmessages() should not be called with an identifier (%s) present in self.callbacks" % identifier)
        endtime = time.time() + timeout
        while identifier not in self.messages:
            time.sleep(0.04)
            if time.time() > endtime:
                break
        if identifier not in self.messages:
            raise exceptions.TimeOut("identifier %s not found in messages within %d seconds. Available identifiers: %s" % (identifier, timeout, str(self.messages.keys())))
        self.acquireMemLock()
        if identifier in self.messages:
            (resultlines, status) = self.messages[identifier]
            del self.messages[identifier]
        self.releaseMemLock()
        return (resultlines, status)
    
    def checkTimeouts(self):
        """Check if the timeouts in callbacks{} have not been passed. If it has, a result was received, 
        but the result was not used."""
        # TODO: decide on return result. En eh, to be written too
        pass
    
    def callback(self, function, resultlines, status=None):
        """Call function with resultlines as argument. Either in a new thread or simply the current thread."""
        if self.threadedcallback:
            name = function.__name__ + " callback"
            if self.hasStatusArgument(function):
                arguments = (resultlines, status) # create a tuple
            else:
                arguments = (resultlines,) # create a tuple
            callbackthread = threading.Thread(target=function, name=name, args=arguments)
            callbackthread.start()
            self.callbackthreads.append(callbackthread)
        else:
            if self.hasStatusArgument(function):
                function(resultlines, status)
            else:
                function(resultlines)
    
    def processMessage(self, message):
        """Calls parseMessage and checks the type of the message. Calls the callback function for autonomous 
        messages or regular results with a known callback function. Otherwise, simply add the message to 
        the messages dictionary, so it can be retrieved by getmessage() in another thread."""
        logger = logging.getLogger("protocols")
        (resultlines, identifier, status) = self.parseMessage(message)
        autotype = self.isAutonomousType(identifier, status)
        if (autotype != False):
            # Autonomous message
            if autotype in self.autocallbacks:   # specific callback function
                callback = self.autocallbacks[autotype]
                logger.info("Sending autonomous message (type %s, identifier %s) to %s()" % (autotype,identifier,callback.__name__))
                self.callback(callback, resultlines, status=status)
            elif True in self.autocallbacks:  # catch-all callback function
                callback = self.autocallbacks[True]
                logger.info("Sending autonomous message (type %s, identifier %s) to %s()" % (autotype,identifier,callback.__name__))
                self.callback(callback, resultlines, status=status)
            else:
                logger.info("Skipping unhandled autonomous message (type %s, identifier %s)" % (autotype,identifier))
            return
        callback = None
        self.acquireMemLock()
        if identifier in self.callbacks:
            # regular message, with known callback function
            (callback, timeout) = self.callbacks[identifier]
            del self.callbacks[identifier]
        self.releaseMemLock()
        if callback:
            logger.info("Sending regular message with identifier %s to %s()" % (identifier,callback.__name__))
            self.callback(callback, resultlines, status)
        else:
            # regular message
            self.acquireMemLock()
            if identifier in self.messages:
                raise CommandFailed("Can't append result with identifier %s: a result with the same identifer already exists." % identifier)
            logger.debug("Appending message result with identifier %s to messages queue" % (identifier))
            self.messages[identifier] = (resultlines, status)
            self.releaseMemLock()
    
    def fetchMessages(self):
        """Function in a separate thread. Repeatedly call readmessage(timeout=infinity), and 
        processMessage() with ayny possible result. The thread is stopped if dorun is set to False.
        Call CheckTimeouts() every once in a while"""
        timeout = max(2,int(self.timeout/3)) # a short timeout (max 2 sec.), so we're quickly back in the loop
        logger = logging.getLogger("protocols")
        logger.debug("Asynchronously fetching messages with %0.1f second interval" % (timeout))
        while (self.dorun == True) or (len(self.callbacks) > 0):
            try:
                message = self.readmessage(timeout=timeout)
                # logger.debug("Got %d bytes of data" % (len(message)))
                self.processMessage(message)
            except exceptions.TimeOut:
                logger.debug("Waiting for data")
                pass
            self.checkTimeouts()
    
    def createThreads(self):
        """Initializes internal variables, and start listening thread. This function is called
        after login() and authorize() are called."""
        self.messages  = {}
        self.callbacks = {}
        self.callbackthreads = []
        name = "Thread-"+self.getTarget()+"-receiver"
        self.receivethread = threading.Thread(target=self.fetchMessages, name=name)
        self.dorun = True
        self.receivethread.start()
    
    def stopThreads(self, timeout=None):
        # Signal thread to stop, and stop it with a timeout
        logger = logging.getLogger("protocols")
        self.dorun = False
        if timeout == None:
            timeout = 1.2*self.timeout # Add a little margin; we may have to wait for many connections..
        logger.debug("Stopping receiver threads (with %d sec timeout)" % timeout)
        self.receivethread.join(timeout=timeout)
        logger.debug("Stopping %d parser threads (with %d sec timeout each)" % (len(self.callbackthreads), timeout))
        for callbackthread in self.callbackthreads:
            callbackthread.join(timeout=timeout)
        if len(self.messages) > 0:
            logger.error("Unprocessed messages left in queue with id %s, after stopping listener thread" % str(self.messages.keys()))
        if self.receivethread.isAlive():
            logger.error("Receiver thread is still active, despite an attempt to stop it.")
    
    def acquireMemLock(self):
        """Acquires memory lock. This function can only be called after start() has been called"""
        return self.memlock.acquire() # blocking
        # WARNING: Function with time-out doesn't work very well, because of the delay
        # (thread A never got the lock, since thread B held the lock for a long time, and 
        # got it back before A -- apparently it was not handed out in request order)
        # gotlock = False
        # endtime = time.time() + 10 # 10 sec timeout
        # logger = logging.getLogger("protocols")
        # (callerfilename, linenumber, callername, text) = traceback.extract_stack()[-2]
        # logger.debug("Acquire memory lock id %s from %s() in file %s by thread %s" % (id(self.loglock), callername, callerfilename, threading.currentThread().getName()))
        # while True:
        #     gotlock = self.memlock.acquire(False) # non-blocking
        #     if gotlock:
        #         break
        #     if time.time() > endtime:
        #         raise exceptions.TimeOut("Unable to get a memory lock in 10 seconds.")
        #     time.sleep(0.05)
        # return gotlock;
    
    def releaseMemLock(self):
        """Releases memory lock. You MUST never call releaseMemLock() if you didn't acquire it first."""
        # logger = logging.getLogger("protocols")
        # logger.debug("Release memory lock id %s" % id(self.memlock))
        self.memlock.release()
        return True;
    
    def acquireLoglock(self):
        """Acquires I/O lock. This function can only be called after start() has been called"""
        gotlock = False
        endtime = time.time() + 10 # 10 sec timeout
        # logger = logging.getLogger("protocols")
        # logger.debug("Acquire log lock by thread %s" % (threading.currentThread().getName()))
        while True:
            gotlock = self.iolock.acquire(False) # non-blocking
            if gotlock:
                break
            if time.time() > endtime:
                raise exceptions.TimeOut("Thread %s is unable to get a log lock in 10 seconds." % (threading.currentThread().getName()))
            time.sleep(0.05)
        return gotlock;
    
    def releaseLoglock(self):
        """Releases I/O lock. You MUST never call releaseMemLock() if you didn't acquire it first."""
        # logger = logging.getLogger("protocols")
        # logger.debug("Release log lock by thread %s" % (threading.currentThread().getName()))
        self.iolock.release()
        return True;
    
    def start(self):
        """Make sure the actual I/O for the file or device is ready. logs in, authorize.
        You shouldn't call it more than once"""
        logger = logging.getLogger("protocols")
        logger.debug("Fetching information asynchronous from %s using %s" % (self.getTarget(), type(self).__name__))
        if not self.autocallbacks:
            self.autocallbacks = {}
        self.iolock  = threading.Lock()
        self.memlock = threading.Lock()
        self.connect()
        self.login()
        self.authorize()  # call authorize while still in sync mode. It uses send_and_receive().
        self.createThreads()
    
    def stop(self):
        """Deauthorizes, logs out, and closes the I/O connection. You shouldn't call it more than once"""
        self.stopThreads()
        self.deauthorize()  # deauthorize used send_and_receive, and is thus synchronous
        self.disconnect()
        self.closeLogFile()
        self.iolock  = None
        self.memlock = None



# Note: methods in first class override methods in later classes
class BaseInput(BaseIOInput, BaseLangInput, BaseAsyncInput):
    """A base input class, consisting of three parts working togther: 
    the I/O, Language and Command part"""
    pass


