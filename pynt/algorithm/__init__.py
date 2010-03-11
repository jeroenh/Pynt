# -*- coding: utf-8 -*-
"""Generic algorithm package. The only type of supported algorithm at the moment is 
a broadcast and traceback algorithm, which can find end-points in a multilayer pynt. 
These algorithms are prototypes only, designed to show that path finding is possible 
in the first place. They are not designed for speed."""

# standard modules
import logging
import sys
import time

# local modules
import pynt.elements
import pynt.layers
import pynt.paths
import pynt.algorithm.output



# Three checks for the algorithm variants:
# - channelsAvailable(): are enough channels available (only checked after a "merge" of channels)
# - visitedBefore(): was the switch matrix visited before (with same stack)
# - direction (no loopback, real direction)
# this last check SHOULd be checked BEFORE path is created, but with ccp list
# However, in practice, they are embedded in visitedBefore() or channelsAvailable() for quick-hack-"reasons"
# note that loopbacks are OK for potential interfaces at switchmatrices with label switching)



class InvalidPath(Exception):
    """Exception raised by a sub routine upon finding that the current path will never be a valid shortest path, for whatever reason."""
    pass



class BaseAlgorithm(object):
    """Algorithm for path finding and path walking. This is an implementation of a bread first 
    search algorithm, very much geared towards networks. In particular, """
    outerleaves     = None
    progressPrinters = None
    # tree = None
    kshortestpath   = 1     # return first solution only
    metriclimit     = 75.0  # stop if the path exceeds this length
    custommetrics   = {}  # dict of ConnectionClass: metric
    sourcecp        = None
    destinationcp   = None
    solution        = None  # algorithm-specific, for example a Path or list of Path objects
    _runalgorithm   = False # True if algorithm was run
    progressfunc    = None  # Callback function, called for each step as progressfunc(count, path, leaves, note)
    def __init__(self):
        self.outerleaves = []
        # self.tree = []
        self.custommetrics = {}
        self.solution    = []
        self.setPrinter(pynt.algorithm.output.defaultProgressPrinter())
    
    def setPrinter(self, output):
        assert(isinstance(output, pynt.algorithm.output.ProgressPrinter))
        self.progressPrinters = [output]
    
    def addPrinter(self, output):
        assert(isinstance(output, pynt.algorithm.output.ProgressPrinter))
        self.progressPrinters.append(output)
    
    def getPrinters(self):
        return self.progressPrinters
    
    def removePrinter(self, output):
        assert(isinstance(output, pynt.algorithm.output.ProgressPrinter))
        self.progressPrinters.remove(output)
    
    def setEndpoints(self, startcp, endcp):
        logger = logging.getLogger("pynt.algorithm")
        self.sourcecp = startcp
        self.destinationcp = endcp
        if startcp.getLayer() != endcp.getLayer():
            logger.error("Layers of end points %s and %s do not match: %s and %s" % (startcp, endcp, startcp.getLayer(), endcp.getLayer()))
    
    def setConstraints(self, metriclimit=40.0):
        self.metriclimit = metriclimit
    
    def setMetricLimit(self, limit):
        self.metriclimit = limit
    
    def setCustomMetric(self, connectionClass, metric):
        """Changes the metric of a specific connectionClass (and its children)"""
        assert(issubclass(connectionClass, pynt.paths.Connection))
        self.custommetrics[connectionClass] = float(metric)
    
    def getCustomMetric(self, connectionClass):
        pass
        # if connectionClass, or one of it's parent classes is in self.custommetric, return that.
        # TODO: how to loop the class tree? As inspect.getclasstree(()?
    
    def createConnection(self, connectionClass, *param, **args):
        """Return a new object of the given connectionClass, and set the metric based 
        on the custom paramter.
        """
        assert(issubclass(connectionClass, pynt.paths.Connection))
        try:
            connection = connectionClass(*param, **args)
        except TypeError, e:
            raise TypeError("Can't create %s(%s, %s): %s" % (connectionClass.__name__, param, args, e))
        metric = self.getCustomMetric(connectionClass)
        if metric != None:
            connection.metric = metric
        return connection
    
    def findShortestPath(self):
        if not self._runalgorithm:
            starthop = self.createHop(self.sourcecp, pynt.paths.StartingPoint(), pynt.paths.Path())
            self.outerleaves.append(starthop.getPath())
            self.breadthfirstsearch()
            self._runalgorithm = True
        return self.solution
    
    def breadthfirstsearch(self):
        logger = logging.getLogger("pynt.algorithm")
        logger.log(25, "Starting breadth first search algorithm")
        c = 0
        self.printProgressHeader()
        while True:
            note = ""
            if len(self.outerleaves) == 0:
                logger.warning("No more leaves to parse after %d iterations; %d paths found" % (c,len(self.solution)))
                break
            # walk all outerleaves, finding the one with the smallest metric
            logger.debug("Find smallest metric of %d outer leaves" % len(self.outerleaves))
            smallmetricpath  = self.getSmallestMetricLeaf()
            logger.debug("Examining path %s" % smallmetricpath)
            # if this is the destination hop, and the stack is empty:
            #   store in solution.
            if smallmetricpath.getLastHop().getConnectionPoint() == self.destinationcp:
                stack = smallmetricpath.getStack()
                if stack.isempty():
                    # we reached our goal!
                    self.solution.append(smallmetricpath)
                    logger.log(25, "Destination reached in %d hops after %d iterations" % (len(smallmetricpath), c))
                else:
                    logger.warning("Reached end-node %s with non-empty stack %s. Continuing." % (self.destinationcp, stack))
            # stop algorithm if len (solution) > k. we're done, and have success.
            #   (give warning if it is the destination, but stack is not empty)
            if self.stopAlgorithm(smallmetricpath.getMetric()):
                break
            # else:
            # call getValidNextHopList for the hop with smallest metric
            #    append the result to outerleaves, and remove the given hop.
            else:
                newpaths = self.getValidExtendedPaths(smallmetricpath)
                sys.stderr.flush()  ### TODO: remove (debug only)
                sys.stdout.flush()  ### TODO: remove (debug only)
                for newpath in newpaths:
                    self.outerleaves.append(newpath)
                    if newpath.getLastHop().getConnectionPoint() == self.destinationcp:
                        note += " (solution)"
                self.outerleaves.remove(smallmetricpath)
                c += 1
                if len(newpaths) > 1:
                    note += " (branching)"        
                self.printProgress(c, smallmetricpath, note)
        self.printProgressFooter()
    
    def printProgressHeader(self):
        for output in self.getPrinters():
            output.printProgressHeader()
    
    def printProgress(self, count, path, note):
        for output in self.getPrinters():
            output.printProgress(count, path, self.outerleaves, note)
    
    def printProgressFooter(self):
        for output in self.getPrinters():
            output.printProgressFooter()
    
    def printSolution(self):
        for output in self.getPrinters():
            output.printSolutions(self.solution)
    
    def isSolution(self, path):
        if (path.getLastHop().getConnectionPoint() == self.destinationcp):
            stack = path.getStack()
            if stack.isempty():
                return True
        return False
    
    def stopAlgorithm(self, currentmetric):
        """Return True if the algorithm may stop."""
        logger = logging.getLogger("pynt.algorithm")
        #self.minsolutionmetric
        #self.maxsolutionmetric        
        ##self.getequalmetricsolutions = False  # get all solutions of the same metric
        if len(self.solution) >= self.kshortestpath:
            return True
        #if getequallengthsolution:
        #    return # not written
        if currentmetric > self.metriclimit:
            logger.warning("Reached metric limit %.2f; %d paths found" % (self.metriclimit, len(self.solution)))
            return True
        return False
    
    def getSmallestMetricLeaf(self):
        """return the leaf with the smallest metric"""
        if len(self.outerleaves) == 0:
            return None
        smallestleaf  = self.outerleaves[0]
        smallestmetric = self.outerleaves[0].getMetric()  # get a starting value
        for leaf in self.outerleaves:  # leaves is a list of Paths
            if leaf.getMetric() <= smallestmetric:  # < gives first match, <= gives last match
                # we want last match, since that looks most like previous one (looks better in path finding vizualisation)
                smallestleaf  = leaf
                smallestmetric = leaf.getMetric()
        return smallestleaf
    
    def getValidExtendedPaths(self, path):
        """Returns a list of possible paths, one distance longer then the given Path, 
        making it is still valid. To conserve resources, this goes in a few steps:
        1. getNextCCpList() quickly get a list of (connection, connection point)
        2. createHop() objects (this can be a very expensive operation)
        3. check IsValidPath(hop) to see if the path with new hop is really valid"""
        logger = logging.getLogger("pynt.algorithm")
        hop    = path.getLastHop()
        curcp  = hop.getConnectionPoint()
        if len(path) >= 2:
            prevcp = path[-2].getConnectionPoint()
        else:
            prevcp = None
        alloweddirections = self.getAllowedNextDirections(path)
        nextccps = self.getNextCCpList(curcp, prevcp, alloweddirections)
        nexthops = []
        validpaths = []
        if len(nextccps) > 1:
            # we will branch the tree. Make sure each branch uses it's own values by smart-copying the path
            logger.info("Branching path %s in %d branches" % (path, len(nextccps)))
            # Note: copying a path is a time-consuming operation, and should be avoided if possible.
            path = path.copy()
        for (nextconnection, nextcp) in nextccps:
            nexthop = None
            try:
                nexthop = self.createHop(nextcp, nextconnection, path)
                if self.IsValidPath(nexthop.path):
                    validpaths.append(nexthop.path)
            except InvalidPath, e:
                if nexthop != None:
                    nextpath = nexthop.path
                else:
                    nextpath = path
                logger.info("Terminate path %s: %s" % (nextpath, e))
        if len(nextccps) == 0:
            logger.info("Terminate path %s: no connections points towards direction(s) %s found" % (path, alloweddirections))
        return validpaths
    
    def getAllowedNextDirections(self, path):
        return path.getLastHop().getPreviousConnection().nextdirection
    
    def getNextCCpList(self, cp, prevcp=None, direction=[pynt.paths.directionInternal, pynt.paths.directionExternal]):
        """Return a list of possible (connection, connection point) (c+cp), one distance from the given connection point.
        The only filter we have is a custom direction object, which is typically a list, but is algorithm-specific.
        Typicall directions are internal/external/adaptation/deadaptation. By default, use directionAll"""
        logger = logging.getLogger("pynt.algorithm")
        logger.debug("Find list of type '%s' connections from %s" % (direction, cp))
        ccplist = []
        if pynt.paths.directionInternal in direction:
            extendlist = self.getNextPotentialSwitchToList(cp)
            logger.debug("Found %d potential switch to interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
            extendlist = self.getNextPotentialDeAdaptationList(cp)
            logger.debug("Found %d potential client interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
        if pynt.paths.directionExternal in direction:
            extendlist = self.getNextLinkToList(cp)
            logger.debug("Found %d linked to interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
            extendlist = self.getNextPotentialAdaptationList(cp)
            logger.debug("Found %d potential server interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
        return ccplist
    
    def getNextActualSwitchToList(self, cp):
        """Return a list tuples (SwitchToConnection, connection point) for each 
        actual switchedTo (including packet and circuit switchedto) from the 
        given cp to another interface."""
        ccplist = []
        switchmatrix = cp.getSwitchMatrix()
        if switchmatrix:
            for intf in switchmatrix.getActualSwitchedInterfaces(cp, bidirectional=True):
                connection = self.createConnection(pynt.paths.SwitchMatrixConnection, switchmatrix)
                ccplist.append((connection, intf))
        else:
            for intf in cp.getActualSwitchedInterfaces(bidirectional=True):
                connection = self.createConnection(pynt.paths.SwitchToConnection)
                ccplist.append((connection, intf))
        return ccplist
    
    def getNextPotentialSwitchToList(self, cp):
        """Return a list tuples (SwitchToConnection, connection point) for each 
        potential switchedTo (including configurable, as those are clearly can be created) 
        from the given cp to another interface."""
        ccplist = []
        switchmatrix = cp.getSwitchMatrix()
        if switchmatrix:
            #print "%s: %s -> ? (potential switched interfaces)" % (switchmatrix.getName(), cp)
            for intf in switchmatrix.getPotentialSwitchedInterfaces(cp, bidirectional=True):
                connection = self.createConnection(pynt.paths.SwitchMatrixConnection, switchmatrix)
                ccplist.append((connection, intf))
            #print "%s: %s -> %s" % (switchmatrix.getName(), cp, [ccp[1].getName() for ccp in ccplist])
        else:
            for intf in cp.getPotentialSwitchedInterfaces(bidirectional=True):
                connection = self.createConnection(pynt.paths.SwitchToConnection)
                ccplist.append((connection, intf))
        return ccplist
    
    def getNextAvailableSwitchToList(self, cp):
        """Return a list tuples (SwitchToConnection, connection point) for each 
        potential switchedTo (including configurable, as those are clearly can be created) 
        from the given cp to another interface."""
        ccplist = []
        switchmatrix = cp.getSwitchMatrix()
        if switchmatrix:
            # print "%s: %s %s>%s -> ? (available switched interfaces)" % (switchmatrix.getName(), cp, cp.ingressLabelSetToStr(), cp.internalLabelSetToStr())
            for intf in switchmatrix.getAvailableSwitchedInterfaces(cp, bidirectional=True):
                connection = self.createConnection(pynt.paths.SwitchMatrixConnection, switchmatrix)
                ccplist.append((connection, intf))
            # print "%s: %s -> %s" % (switchmatrix.getName(), cp, [ccp[1].getName() for ccp in ccplist])
        else:
            for intf in cp.getAvailableSwitchedInterfaces(bidirectional=True):
                connection = self.createConnection(pynt.paths.SwitchToConnection)
                ccplist.append((connection, intf))
        return ccplist
    
    def getNextLinkToList(self, cp):
        """Return a list tuples (LinkToConnection, connection point) for each 
        linkedTo (including those in a broadcastsegment) from the given cp to another 
        interface."""
        ccplist = []
        for intf in cp.getLinkedInterfacesOnly():
            connection = self.createConnection(pynt.paths.LinkToConnection)
            ccplist.append((connection, intf))
        broadcastsegment = cp.getBroadcastSegment()
        if broadcastsegment:
            for intf in broadcastsegment.getOtherInterfaces(cp):
                connection = self.createConnection(pynt.paths.BroadcastSwitchToConnection, broadcastsegment)
                ccplist.append((connection, intf))
        return ccplist
    
    def getNextConnectedToList(self, cp):
        """Return a list tuples (ConnectedToConnection, connection point) for each 
        connectedTo (including linkedTo) from the given cp to another interface."""
        ccplist = []
        # We want connected interfaces only, because linked interfaces will 
        # otherwise be returned as well!
        for intf in cp.getConnectedInterfacesOnly():
            connection = self.createConnection(pynt.paths.ConnectedToConnection)
            ccplist.append((connection, intf))
        return ccplist
    
    def getNextActualAdaptationList(self, cp):
        """Return a list tuples (AdaptationConnection, connection point) for each 
        server layer interface from the given cp to another interface."""
        ccplist = []
        adaptationfunction = cp.getServerAdaptationFunction()
        if adaptationfunction == None:
            return []
        for intf in cp.getServerInterfaces():
            connection = self.createConnection(pynt.paths.AdaptationConnection, adaptationfunction)
            ccplist.append((connection, intf))
        return ccplist
    
    def getNextPotentialAdaptationList(self, cp):
        """Return a list tuples (AdaptationConnection, connection point) for each 
        server layer interface from the given cp to another interface, both actual 
        and potential server layer interfaces."""
        ccplist = []
        for (intf,adaptationfunction) in cp.getAllServerTuples():
            connection = self.createConnection(pynt.paths.AdaptationConnection, adaptationfunction)
            ccplist.append((connection, intf))
        return ccplist
    
    def getNextAvailableAdaptationList(self, cp):
        """Return a list tuples (AdaptationConnection, connection point), reachable from 
        the given connecion point cp. Also set the metric of the connection.
        getNextAvailableAdaptationList() seems logical equivalent with getNextPotentialAdaptationList()."""
        return self.getNextPotentialAdaptationList(cp)
    
    def getNextActualDeAdaptationList(self, cp):
        """Return a list tuples (AdaptationConnection, connection point) for each 
        client layer interface from the given cp to another interface."""
        ccplist = []
        adaptationfunction = cp.getClientAdaptationFunction()
        if adaptationfunction == None:
            return []
        for intf in cp.getClientInterfaces():
            connection = self.createConnection(pynt.paths.DeAdaptationConnection, adaptationfunction)
            ccplist.append((connection, intf))
        return ccplist
    
    def getNextPotentialDeAdaptationList(self, cp):
        """Return a list tuples (AdaptationConnection, connection point) for each 
        server layer interface from the given cp to another interface, both actual 
        and potential server layer interfaces."""
        ccplist = []
        for (intf,adaptationfunction) in cp.getAllClientTuples():
            connection = self.createConnection(pynt.paths.DeAdaptationConnection, adaptationfunction)
            ccplist.append((connection, intf))
        return ccplist
    
    def getNextAvailableDeAdaptationList(self, cp):
        """Return a list tuples (AdaptationConnection, connection point), reachable from 
        the given connecion point cp. Also set the metric of the connection.
        getNextAvailableDeAdaptationList() seems logical equivalent with getNextPotentialDeAdaptationList()."""
        return self.getNextPotentialDeAdaptationList(cp)
    
    def IsValidPath(self, path):
        """Verifies if a path is valid. Only the last hop in the path has to be checked; 
        it can be assumed that the rest of the path has been checked earlier. 
        By default, it is valid as long as each connection point (including potential interfaces) 
        is only used once. This is obviously overridden by algorithm classes.
        Typical checks to perform are:
        - is the adaptation stack valid, especially if the connection is De-Adaptation
        - does the current connection point further restrict the number of allowed labels
        - are there more available labels left then the interfacecount
        - does the current connection point restrict the number of layer Properties to None
        - does it not give a loop (i.e. has the interface been used before, with the same stack)
          (note that this a non-obvious check in multi-layer networks: data may get transported 
          through two channels (first one, later the other), which use the same physical interface)
        - is the configuration not forbidden because an earlier configuration (e.g., we can't use 
          the same VLAN if it was already used earlier in the same path)
        - etc., etc.
        """
        logger = logging.getLogger("pynt.algorithm")
        logger.debug("Validate path: %s" % path)
        if len(path) < 2:
            raise InvalidPath("Path length < 2; can't get previous hop")
        hop = path.getLastHop()
        prevhop = path[-2]
        assert(hop.getPath() == path)
        return True
        #connection = hop.getPreviousConnection()
        #if isinstance(connection, pynt.paths.DeAdaptationConnection):
        #    prevstack = prevhop.getStack()
        #    stack     = hop.getStack()
        #    if len(stack) != len(prevstack)-1:
        #        logger.info("Terminate path %s: de-adaptation did pop lowest layer from stack" % (path))
        #        return False
        #logger.debug("Path is valid: %s: no irregularities found" % (path))
        #return True
    def visitedMatrixBefore(self, path):
        """Checks if a path goes through an switch matrix that has been used before
        *in this path*with the same stack and the same or a subset of available labels 
        as the first time (if the link did not work the first try, it won't work now)
        """
        ########### TODO: to be written!!
        lasthop = path.getLastHop()
        lastcp = lasthop.getConnectionPoint()
        stack = path.getStack()
        #connection = lasthop.getPreviousConnection()
        #assert isinstance(connection, pynt.paths.SwitchMatrixConnection)
        #switchmatrix = connection.switchmatrix
        #print "Processing %s / %s:\n  %s" % (switchmatrix, cp, stack)
        for i in range(0,len(path)-2): # loop from first to one-but-last connection point.
            if path[i].getConnectionPoint() == lastcp:
                visitedstack = path[i].getStack()
                if stack.issubset(visitedstack): # we already visited this cp before with same stack
                    return True
        return False
    def channelsAvailable(self, path):
        """Checks if the last connection point in a path contain enough 
        free channels, taking previous use of the same connection point
        into account. This is checkedby looking at the number of available labels.
        """
        if len(path) < 2:
            return True
        lasthop = path.getLastHop()
        ismerge = False
        lastcp = lasthop.getConnectionPoint()
        prevcp = path[-2].getConnectionPoint()
        # fill hops with hops with the same connection point at the last connection point
        hops = [lasthop]
        for i in range(1,len(path)-1):
            if path[i].getConnectionPoint() == lastcp:
                if prevcp not in [path[i-1].getConnectionPoint(), path[i+1].getConnectionPoint()]: # different next/previous hop: it is a merge
                    hops.append(path[i])
                    ismerge = True
        if ismerge:
            # First connectionpoint after merge of two channels
            # (this can be either two adaptations into a single interface or two switchTo in a single interface.)
            if not isinstance(lastcp, pynt.elements.PotentialMuxInterface):
                return False  # Can't use non-potential interface for a merge.
            # The number of available channels is defined by:
            # - the size of the available labelset
            # - the client count of the underlying adaptation.
            # - the server count of the adaptation above, if any.
            # TODO: we currently only check the size of the available labelset, which works in 95% of the cases.
            # Make sure enough channels are available.
            availablechannels = len(lastcp.getLabelSet())
            if availablechannels == 0:
                return False  # no channels, can only use interface once
            for hop in hops:
                layerprop = hop.getStack().getLowestLayer()
                if layerprop != None:
                    availablechannels -= layerprop.getInterfaceCount()
                else:
                    availablechannels -= 1
                if availablechannels <= 0:
                    return False # no more channels available
        elif len(hops) > 1:
            connection = lasthop.getPreviousConnection()
            if isinstance(connection, pynt.paths.AdaptationConnection):
                # Check if last adaptation is same as others
                layerprop = lasthop.getStack().getLowestLayer()
                adaptationfunction = layerprop.adaptationfunction
                for hop in hops:
                    layerprop = hop.getStack().getLowestLayer()
                    if adaptationfunction != layerprop.adaptationfunction:
                        # We got here using a different adaptation function. 
                        # Most likely an interface that can handle multiple adaptations.
                        # Abort; such interface can only support a single adaptation at the same time.
                        return False
        return True
    def createHop(self, nextcp, nextconnection, path):
        """Return a hop object, given the path, next connection and next connection point.
        Note that the hop will contain pointers to all previous . If you branch the path,
        you must make a copy of the path (in particular of all LayerProperties in the stacks 
        of each hop in the path), before handing it to this function. See Path.copy()"""
        assert(isinstance(nextcp, pynt.elements.ConnectionPoint))
        assert(isinstance(nextconnection, pynt.paths.Connection))
        assert(isinstance(path, pynt.paths.Path))
        logger = logging.getLogger("pynt.algorithm")
        stack  = path.getStack()
        logger.debug("Creating Hop of (%s) %s %s" % (nextconnection.getDescription(), type(nextcp).__name__, nextcp.getURIdentifier()))
        if isinstance(nextconnection, pynt.paths.AdaptationConnection):      # increase the stack (always create a copy!)
            stackelt = self.getLayerProperty(nextconnection, nextcp)
            stack = pynt.paths.Stack(stack[:])  # make a copy of the stack.
            stack.append(stackelt)
            # print ("Interface %s: " % nextcp), stack.getLowestLayer().LabelsToStr()
        elif isinstance(nextconnection, pynt.paths.DeAdaptationConnection):    # decrease the stack
            try:
                stack = pynt.paths.Stack(stack[:])  # make a copy of the stack.
                stackelt = stack.pop()
            except IndexError:
                raise InvalidPath("Can not de-adapt; stack is empty")
            # If the last adaptation was a multiplexing adaptation function, 
            # copy the ingress and egress label. Otherwise, allow all possible labels.
            if not nextcp.hasExternalLabel():
                # interface has no external label. We must reset the allowed label values with the default values (of the interface, or the layer)
                stack.duplicateLowestLayer()
                # print "Interface %s has no external labels after de-adaptation:" % nextcp
                # print "before", stack.getLowestLayer().LabelsToStr()
                layerprop = stack.getLowestLayer()
                if layerprop:
                    layerprop.setvaluesFromCp(nextcp)
                # print "after", stack.getLowestLayer().LabelsToStr()
            # else:
            #     print ("Interface %s: (demultiplexed)" % nextcp), stack.getLowestLayer().LabelsToStr()
        elif isinstance(nextconnection, pynt.paths.StartingPoint):               # initialize the stack
            stackelt = self.getLayerProperty(nextconnection, nextcp)
            stack.append(stackelt)
            # print ("Interface %s: " % nextcp), stack.getLowestLayer().LabelsToStr()
        elif isinstance(nextconnection, pynt.paths.LinkToConnection):
            # If the last adaptation was a multiplexing adaptation function, 
            # copy the ingress and egress label. Otherwise, allow all possible labels.
            if not nextcp.hasExternalLabel():
                # interface has no external label. We must reset the allowed label values with the default values (of the interface, or the layer)
                stack.duplicateLowestLayer()
                # print "Interface %s has no external labels after link:" % nextcp
                # print "before", stack.getLowestLayer().LabelsToStr()
                layerprop = stack.getLowestLayer()
                layerprop.setvaluesFromCp(nextcp)
                # print "after", stack.getLowestLayer().LabelsToStr()
            # else:
            #     print ("Interface %s: (after channel/link)" % nextcp), stack.getLowestLayer().LabelsToStr()
        elif isinstance(nextconnection, pynt.paths.SwitchToConnection):
            # TODO: copy the existing label set if the switch matrix has NO swapping capability. 
            # Otherwise, allow all possible labels.
            # Now it only copies, never allowing all possible labels.
            layerprops = stack.getLowestLayer()
            # print ("Interface %s: (unmodified after switchTo)" % nextcp), stack.getLowestLayer().LabelsToStr()
            # TODO: set internal label, possible also external label.
        return pynt.paths.Hop(nextcp, nextconnection, stack, path)
    
    def getLayerProperty(self, connection, cp):
        """Return a LayerProperty object, and fill it with the values based on the given connection and cp.
        You may assume that the connection is always an AdaptationConnection or StartingPoint."""
        layer = cp.getLayer()
        if isinstance(connection, pynt.paths.AdaptationConnection):
            interfacecount     = connection.adaptationfunction.servercount
            adaptationfunction = connection.adaptationfunction
        else:
            interfacecount     = 1
            adaptationfunction = None
        if not interfacecount:
            logger = logging.getLogger("pynt.algorithm")
            logger.warning("Server layer count of adaptation %s is not defined. Assuming 1." % connection.adaptationfunction)
            interfacecount = 1
        stackelt = pynt.paths.LayerProperty(layer, adaptationfunction, interfacecount)
        stackelt.setvaluesFromCp(cp)
        return stackelt
    
# TODO: move PathFind to own module

class PathFind(BaseAlgorithm):
    """base Path finding class."""
    def getNextCCpList(self, cp, prevcp=None, direction=[pynt.paths.directionInternal, pynt.paths.directionExternal]):
        """Return a list of possible (connection, connection point) (c+cp), one distance from the given connection point.
        The only filter we have is a custom direction object, which is typically a list, but is algorithm-specific.
        Typicall directions are internal/external/adaptation/deadaptation. By default, use directionAll"""
        logger = logging.getLogger("pynt.algorithm")
        logger.debug("Find list of type '%s' connections from %s" % (direction, cp))
        ccplist = []
        if pynt.paths.directionInternal in direction:
            extendlist = self.getNextPotentialSwitchToList(cp)
            logger.debug("Found %d potential switch to interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
            extendlist = self.getNextPotentialDeAdaptationList(cp)
            logger.debug("Found %d potential client interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
        if pynt.paths.directionExternal in direction:
            extendlist = self.getNextLinkToList(cp)
            logger.debug("Found %d linked to interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
            extendlist = self.getNextPotentialAdaptationList(cp)
            logger.debug("Found %d potential server interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
        return ccplist
    

class PFTopology(PathFind):
    """Path find, taking only topology into account, ignoring the specifics of adaptations."""
    def IsValidPath(self, path):
        """Verifies if a path is valid. Only the last hop in the path has to be checked; 
        it can be assumed that the rest of the path has been checked earlier. 
        By default, it is valid as long as each connection point (including potential interfaces) 
        is only used once. This is obviously overridden by algorithm classes.
        Typical checks to perform are:
        - is the adaptation stack valid, especially if the connection is De-Adaptation
        - does the current connection point further restrict the number of allowed labels
        - are there more available labels left then the interfacecount
        - does the current connection point restrict the number of layer Properties to None
        - does it not give a loop (i.e. has the interface been used before, with the same stack)
          (note that this a non-obvious check in multi-layer networks: data may get transported 
          through two channels (first one, later the other), which use the same physical interface)
        - is the configuration not forbidden because an earlier configuration (e.g., we can't use 
          the same VLAN if it was already used earlier in the same path)
        - etc., etc.
        """
        logger = logging.getLogger("pynt.algorithm")
        logger.debug("Validate path: %s" % path)
        if len(path) < 2:
            raise InvalidPath("path length < 2; can't get previous hop")
        hop = path.getLastHop()
        prevhop = path[-2]
        assert(hop.getPath() == path)
        connection = hop.getPreviousConnection()
        if isinstance(connection, pynt.paths.DeAdaptationConnection):
            prevstack = prevhop.getStack()
            stack     = hop.getStack()
            if len(stack) != len(prevstack)-1:
                raise InvalidPath("de-adaptation did pop lowest layer from stack")
            if connection.adaptationfunction.getClientLayer() != stack.getLowestLayer().getLayer():
                raise InvalidPath("de-adaptation %s does not match adaptation %s" % (connection.adaptationfunction, prevstack.getLastAdaptationFunction()))
        if not self.channelsAvailable(path):
            raise InvalidPath("connection point %s exhausted available channels (it is already used earlier in the path)" % (path.getLastHop().getConnectionPoint()))
        if isinstance(connection, pynt.paths.SwitchMatrixConnection) and self.visitedMatrixBefore(path):
            raise InvalidPath("switch matrix %s processed before" % (connection.switchmatrix))
        logger.debug("Path is valid: %s: no irregularities found" % (path))
        return True
    

class PFAdaptation(PathFind):
    """Path find, taking topology and adaptations into account, ignoring available labels."""
    def IsValidPath(self, path):
        """Verifies if a path is valid. Only the last hop in the path has to be checked; 
        it can be assumed that the rest of the path has been checked earlier. 
        By default, it is valid as long as each connection point (including potential interfaces) 
        is only used once. This is obviously overridden by algorithm classes.
        Typical checks to perform are:
        - is the adaptation stack valid, especially if the connection is De-Adaptation
        - does the current connection point further restrict the number of allowed labels
        - are there more available labels left then the interfacecount
        - does the current connection point restrict the number of layer Properties to None
        - does it not give a loop (i.e. has the interface been used before, with the same stack)
          (note that this a non-obvious check in multi-layer networks: data may get transported 
          through two channels (first one, later the other), which use the same physical interface)
        - is the configuration not forbidden because an earlier configuration (e.g., we can't use 
          the same VLAN if it was already used earlier in the same path)
        - etc., etc.
        """
        logger = logging.getLogger("pynt.algorithm")
        logger.debug("Validate path: %s" % path)
        if len(path) < 2:
            raise InvalidPath("path length < 2; can't get previous hop")
        hop = path.getLastHop()
        prevhop = path[-2]
        assert(hop.getPath() == path)
        connection = hop.getPreviousConnection()
        if isinstance(connection, pynt.paths.DeAdaptationConnection):
            prevstack = prevhop.getStack()
            stack     = hop.getStack()
            if len(stack) != len(prevstack)-1:
                raise InvalidPath("de-adaptation did pop lowest layer from stack")
            if connection.adaptationfunction != prevstack.getLastAdaptationFunction():
                raise InvalidPath("de-adaptation %s does not match adaptation %s" % (connection.adaptationfunction, prevstack.getLastAdaptationFunction()))
        if not self.channelsAvailable(path):
            raise InvalidPath("connection point %s exhausted available channels (it is already used earlier in the path)" % (path.getLastHop().getConnectionPoint()))
        if isinstance(connection, pynt.paths.SwitchMatrixConnection) and self.visitedMatrixBefore(path):
            raise InvalidPath("switch matrix %s processed before" % (connection.switchmatrix))
        logger.debug("Path is valid: %s: no irregularities found" % (path))
        return True
    

class PFAvailable(PathFind):
    """Path find, taking topology, adaptation, and available labels into account."""
    def getNextCCpList(self, cp, prevcp=None, direction=[pynt.paths.directionInternal, pynt.paths.directionExternal]):
        """Return a list of possible (connection, connection point) (c+cp), one distance from the given connection point.
        The only filter we have is a custom direction object, which is typically a list, but is algorithm-specific.
        Typicall directions are internal/external/adaptation/deadaptation. By default, use directionAll"""
        logger = logging.getLogger("pynt.algorithm")
        logger.debug("Find list of type '%s' connections from %s" % (direction, cp))
        ccplist = []
        if pynt.paths.directionInternal in direction:
            extendlist = self.getNextAvailableSwitchToList(cp)
            logger.debug("Found %d available switch to interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
            extendlist = self.getNextAvailableDeAdaptationList(cp)
            logger.debug("Found %d available client interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
        if pynt.paths.directionExternal in direction:
            extendlist = self.getNextLinkToList(cp)
            logger.debug("Found %d linked to interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
            extendlist = self.getNextAvailableAdaptationList(cp)
            logger.debug("Found %d available server interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
        return ccplist
    def IsValidPath(self, path):
        """Verifies if a path is valid. Only the last hop in the path has to be checked; 
        it can be assumed that the rest of the path has been checked earlier. 
        By default, it is valid as long as each connection point (including potential interfaces) 
        is only used once. This is obviously overridden by algorithm classes.
        Typical checks to perform are:
        - is the adaptation stack valid, especially if the connection is De-Adaptation
        - does the current connection point further restrict the number of allowed labels
        - are there more available labels left then the interfacecount
        - does the current connection point restrict the number of layer Properties to None
        - does it not give a loop (i.e. has the interface been used before, with the same stack)
          (note that this a non-obvious check in multi-layer networks: data may get transported 
          through two channels (first one, later the other), which use the same physical interface)
        - is the configuration not forbidden because an earlier configuration (e.g., we can't use 
          the same VLAN if it was already used earlier in the same path)
        - etc., etc.
        """
        logger = logging.getLogger("pynt.algorithm")
        logger.debug("Validate path: %s" % path)
        if len(path) < 2:
            raise InvalidPath("path length < 2; can't get previous hop")
        hop     = path.getLastHop()
        prevhop = path[-2]
        stack   = hop.getStack()
        assert(hop.getPath() == path)
        connection = hop.getPreviousConnection()
        # Verify if the da-adaptation matches the adaptation
        if isinstance(connection, pynt.paths.DeAdaptationConnection):
            prevstack = prevhop.getStack()
            assert(len(stack) == len(prevstack)-1)
            if connection.adaptationfunction != prevstack.getLastAdaptationFunction():
                raise InvalidPath("de-adaptation %s does not match adaptation %s" % (connection.adaptationfunction, prevstack.getLastAdaptationFunction()))
                return False
        # Verify that no resources are used twice
        # It currently checks that no conncetion point is used twice. That is incorrect.
        # It is only a loop if the cp was encountered before and the current stack is a subset of the stack we had earlier.
        lastcp = hop.getConnectionPoint()
        if not self.channelsAvailable(path):
            raise InvalidPath("connection point %s exhausted available channels (it is already used earlier in the path)" % (path.getLastHop().getConnectionPoint()))
        if isinstance(connection, pynt.paths.SwitchMatrixConnection) and self.visitedMatrixBefore(path):
            raise InvalidPath("switch matrix %s processed before" % (connection.switchmatrix))
        # Check for available labels
        curlayerproperties = stack.getLowestLayer()
        if isinstance(connection, pynt.paths.SwitchMatrixConnection):
            #print "%s: %s -> %s" % (connection.switchmatrix.getName(), prevhop.getConnectionPoint(), lastcp)
            labelsofar  = curlayerproperties.getInternalLabelSet()
            curcplabels = lastcp.getInternalLabelSet()
            #print "%s: %s, %s" % (connection.switchmatrix.getName(), labelsofar, curcplabels)
            # print "%s: %s %s -> %s %s" % (connection.switchmatrix.getName(), prevhop.getConnectionPoint(), labelsofar, lastcp, curcplabels)
            # print "\ncomparing previous labelset %s with next labelset %s\n" % (labelsofar, curcplabels)
            if not (labelsofar.isempty() or curcplabels.isempty()):
                # If one of the two (or both) labelset are empty we assume the layer does not have the concept of labels.
                ## WARNING: silly assumption alert. TODO: Use explicit concept of empty labels, rather then this silly one.
                # The problem is that Ethernet has *sometimes* labels.
                switchmatrix = connection.switchmatrix
                if not switchmatrix.isCompatibleLabel(labelsofar, curcplabels):
                    raise InvalidPath("Incompatible Label sets %s and %s" % (labelsofar, curcplabels))
                    return False
                else:
                    newlabels = switchmatrix.possibleLabelsAfterSwitch(labelsofar)
                    newlabels = newlabels & curcplabels
                    #if len(newlabels) > 4000:
                    #    newlabels = labelsofar
                    logging.debug("Label switching at %s: %s (%s) & %s (%s) = %s" % (switchmatrix.getName(), labelsofar, prevhop.getConnectionPoint(), curcplabels, lastcp, newlabels))
                    # print "Label switching at %s: %s (%s) & %s (%s) = %s" % (switchmatrix.getName(), labelsofar, prevhop.getConnectionPoint(), curcplabels, lastcp, newlabels)
                    if newlabels != labelsofar:
                        # Copy the stack, and the current layer property, so that we don't overwrite 
                        # the labels of prevoious interfaces.
                        hop.duplicateStack()
                        stack = hop.getStack()
                        stack.duplicateLowestLayer()
                        curlayerproperties = stack.getLowestLayer()
                        # Now we can change the labels.
                        # TODO: this is wrong. If the switch has external labels, those need to be set too, to the intersection of the curent and new value.
                        curlayerproperties.setInternalLabelSet(newlabels)
                if newlabels.isempty():
                    raise InvalidPath("Incompatible Label sets %s and %s" % (labelsofar, curcplabels))
                curlayerproperties.setLabelSet(newlabels)
        elif isinstance(connection, pynt.paths.SwitchToConnection):
            labelsofar  = curlayerproperties.getLabelSet()
            curcplabels = lastcp.getLabelSet()
            # print "\n\ncomparing previous labelset %s with next labelset %s\n\n\n" % (labelsofar, curcplabels)
            if not (labelsofar.isempty() and curcplabels.isempty()):
                # If both labelset are empty we assume the layer does not have the concept of labels.
                ## WARNING: silly assumption alert. TODO: explicitly check this somehow.
                newlabels   = labelsofar & curcplabels
                if newlabels.isempty():
                    raise InvalidPath("Incompatible Label sets %s and %s" % (labelsofar, curcplabels))
                    return False
                # TODO: This overwrites earlier labels. That is not good if swapping is possible.
                if newlabels != labelsofar:
                    curlayerproperties.setInternalLabelSet(newlabels)
        elif isinstance(connection, pynt.paths.ConnectedToConnection):
            # TODO: For linkTo: use ingress/egress labels
            labelsofar  = curlayerproperties.getEgressLabelSet()
            curcplabels = lastcp.getIngressLabelSet()
            if not (labelsofar.isempty() and curcplabels.isempty()):
                # If both labelset are empty we assume the layer does not have the concept of labels.
                ## WARNING: silly assumption alert. TODO: explicitly check this somehow.
                newlabels   = labelsofar & curcplabels
                if newlabels.isempty():
                    raise InvalidPath("Incompatible Label sets %s and %s" % (labelsofar, curcplabels))
                # TODO: This overwrites earlier labels. That is not good if swapping is possible.
                if newlabels != labelsofar:
                    curlayerproperties.setEgressLabelSet(newlabels)
        logger.debug("Path is valid: %s: no irregularities found" % (path))
        return True
    

# TODO: move PathWalk to own module

class PathWalk(BaseAlgorithm):
    def breadthfirstsearch(self):
        logger = logging.getLogger("pynt.algorithm")
        logger.log(25, "Starting bread first search algorithm")
        print "Try  Hops  Metric Outerleaves in tree"
        print "---- ----- ------ -------------------------------------------------------"
        c = 0
        while True:
            note = ""
            if len(self.outerleaves) == 0:
                logger.warning("No more leaves to parse; %d paths found" % len(self.solution))
                return False # return without a solution
            # walk all outerleaves, finding the one with the smallest metric
            logger.debug("Find smallest metric of %d outer leaves" % len(self.outerleaves))
            smallmetricpath  = self.getSmallestMetricLeaf()
            logger.info("Examining path %s" % smallmetricpath)
            if smallmetricpath.getMetric() > self.metriclimit:
                logger.warning("Reached metric limit %.2f; %d paths found" % (self.metriclimit, len(self.solution)))
            else:
                newpaths = self.getValidExtendedPaths(smallmetricpath)
                for newpath in newpaths:
                    self.outerleaves.append(newpath)
                    if newpath.getLastHop().getConnectionPoint() == self.destinationcp:
                        note += " (solution)"
                    #if len(newpath.getStack()) == 0:
                        self.solution.append(newpath)
                self.outerleaves.remove(smallmetricpath)
                c += 1
                if len(newpaths) > 1:
                    note += " (branching)"
                print "%4d %4d %6.2f %d %s %s" % (c, len(smallmetricpath), smallmetricpath.getMetric(), len(self.outerleaves), len(self.outerleaves)*'.', note)

    def getNextCCpList(self, cp, prevcp=None, direction=[pynt.paths.directionInternal, pynt.paths.directionExternal]):
        """Return a list of possible (connection, connection point) (c+cp), one distance from the given connection point.
        The only filter we have is a custom direction object, which is typically a list, but is algorithm-specific.
        Typicall directions are internal/external/adaptation/deadaptation. By default, use directionAll.
           
        This function is overridden from BaseAlgorithm, because we want actual switched to interfaces, not potential."""
        logger = logging.getLogger("pynt.algorithm")
        logger.debug("Find list of type '%s' connections from %s" % (direction, cp))
        ccplist = []
        if pynt.paths.directionInternal in direction:
            extendlist = self.getNextActualSwitchToList(cp)
            logger.debug("Found %d potential switch to interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
            extendlist = self.getNextActualDeAdaptationList(cp)
            logger.debug("Found %d potential client interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
        if pynt.paths.directionExternal in direction:
            extendlist = self.getNextLinkToList(cp)
            logger.debug("Found %d linked to interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
            extendlist = self.getNextActualAdaptationList(cp)
            logger.debug("Found %d potential server interfaces" % (len(extendlist)))
            ccplist.extend(extendlist)
        return ccplist


class PFTest(PFAvailable):
    def __init__(self):
        BaseAlgorithm.__init__(self)
        self.kshortestpath = 3
        self.metriclimit = 100

class PFDuplicateStackSupression(PFTest):
    pass

class PFShortestPathOnce(PFTest):
    visitedcp       = None  # dict with a list of visited connection points (at switch matrices) with stacks. Used to supress duplicate searches
    def visitedMatrixBefore(self, path):
        """Checks if a path goes through an switch matrix that has been used before
        *in this or any other path* with the same stack and the same or a subset of available labels 
        as the first time (if the link did not work the first try, it won't work now)
        """
        lasthop = path.getLastHop()
        cp = lasthop.getConnectionPoint()
        stack = path.getStack()
        #connection = lasthop.getPreviousConnection()
        #assert isinstance(connection, pynt.paths.SwitchMatrixConnection)
        #switchmatrix = connection.switchmatrix
        #print "Processing %s / %s:\n  %s" % (switchmatrix, cp, stack)
        if self.visitedcp == None:
            self.visitedcp = {}
        if cp not in self.visitedcp:
            self.visitedcp[cp] = [stack.copy()]
            #print "visitedcp[%s] is now %s" % (cp, self.visitedcp[cp])
            return False
        for visitedstack in self.visitedcp[cp]:
            if stack.issubset(visitedstack): # we already visited this cp before
                return True
        self.visitedcp[cp].append(stack.copy())
        return False

class PFExplicitDirection(PFTest):
    def visitedMatrixBefore(self, path):
        return False

class PFNoLoopback(PFTest):
    # WARNING: this algorithm may return false negatives.
    # loopbacks are OK for potential interfaces at switchmatrices with label switching capability
    def getNextCCpList(self, cp, prevcp=None, direction=[pynt.paths.directionInternal, pynt.paths.directionExternal]):
        # remove directional checks
        ccplist = PFAvailable.getNextCCpList(self, cp)
        for ccp in ccplist:
            (nextconn, nextcp) = ccp
            if (nextcp == prevcp) and (not isinstance(nextconn, pynt.paths.SwitchMatrixConnection)):
                ccplist.remove(ccp)
        return ccplist
    def getSmallestMetricLeaf(self):
        """return the leaf with the smallest metric"""
        if len(self.outerleaves) == 0:
            return None
        smallestleaf  = self.outerleaves[0]
        smallestmetric = self.outerleaves[0].getMetric()  # get a starting value
        for leaf in self.outerleaves:  # leaves is a list of Paths
            if leaf.getMetric() < smallestmetric:  # < gives first match, <= gives last match
                # we want FIRST match, and handle it in a FIFO queue: first finish earliest branches, before continuing on deeper branches
                smallestleaf  = leaf
                smallestmetric = leaf.getMetric()
        return smallestleaf
    def visitedMatrixBefore(self, path):
        return False

class PFUnrestrictedFlooding(PFTest):
    def getNextCCpList(self, cp, prevcp=None, direction=[pynt.paths.directionInternal, pynt.paths.directionExternal]):
        # remove directional checks
        return PFAvailable.getNextCCpList(self, cp, prevcp=None)
    def channelsAvailable(self, path):
        """Checks if a path contains a true loop.
        This routine checks if the last interface is already used.
        """
        return True
    def getSmallestMetricLeaf(self):
        """return the leaf with the smallest metric"""
        if len(self.outerleaves) == 0:
            return None
        smallestleaf  = self.outerleaves[0]
        smallestmetric = self.outerleaves[0].getMetric()  # get a starting value
        for leaf in self.outerleaves:  # leaves is a list of Paths
            if leaf.getMetric() < smallestmetric:  # < gives first match, <= gives last match
                # we want FIRST match, and handle it in a FIFO queue: first finish earliest branches, before continuing on deeper branches
                smallestleaf  = leaf
                smallestmetric = leaf.getMetric()
        return smallestleaf
    def visitedMatrixBefore(self, path):
        return False

class PFInterfaceUsedOnce(PFTest):
    def channelsAvailable(self, path):
        """Checks if a path contains a true loop.
        This routine checks if the last interface is already used.
        """
        if len(path) < 2:
            return True
        lasthop = path.getLastHop()
        lastcp = lasthop.getConnectionPoint()
        for pathhop in path[:-1]:
            if pathhop.getConnectionPoint() == lastcp:
                return False
        return True
    def visitedMatrixBefore(self, path):
        return False
