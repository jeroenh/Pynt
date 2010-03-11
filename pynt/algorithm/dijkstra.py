import logging
import sys
import heapq

import pynt.algorithm.output
import pynt.output.dot
import pynt.elements
import pynt.xmlns

infinity = "infinity"

class Dijkstra(pynt.algorithm.BaseAlgorithm):
    """A shortest path algorithm based on Dijkstra's algorithm.
    
    This class implements the Dijkstra's algorithm, and has been tested on network data
    gathered from OSPF output. There is no progress printing; the solution is formed when 
    the algorithm is done running.
    """
    
    def __init__(self, outfile=sys.stdout, subject=None):
        if subject == None:
            self.subjects = None
        elif isinstance(subject, list):
            self.subjects = subject
        elif isinstance(subject, pynt.xmlns.XMLNamespace):
            self.subjects = [subject]
        else:
            raise Exception("Please provide a valid subject for the Dijkstra Algorithm \
                             to search in (or None to search everything.)")
        self.solution = []
        # self.setPrinter(pynt.algorithm.output.defaultProgressPrinter())
        # self.setPrinter(pynt.algorithm.output.TextProgressPrinter())
        self.setPrinter(DijkstraDotSolutionPrinter(outfile=outfile, subject=subject))
        # self.setPrinter(DijkstraEROSolutionPrinter(outfile=outfile, subject=subject))
        self.intraDomain = False
        
    def setPrinter(self, output):
        # assert(isinstance(output, pynt.algorithm.output.ProgressPrinter))
        self.progressPrinters = [output]
    
    # def printProgress(self, count, path, note):
    #     pass
    def printProgressFooter(self):
        pass
    def printProgressHeader(self):
        pass
        
    def setEndpoints(self, startcp, endcp):
        logger = logging.getLogger("pynt.algorithm")
        self.sourcecp = startcp
        self.destinationcp = endcp
        
    def getNeighbors(self, cp):
        if isinstance(cp, pynt.elements.Interface):
            neighbors = []
            for intf in cp.getConnectedInterfacesOnly():
                if cp in intf.getConnectedInterfaces():
                    if self.intraDomain and cp not in self.restrictedGraph:
                        continue
                    else:
                        neighbors.append(intf)
            if cp.getSwitchMatrix():
                neighbors.append(cp.getSwitchMatrix())
            neighbors.append(cp.getDevice())
            if not self.intraDomain and self.subjects:
                return filter(lambda x:x.getNamespace() in self.subjects, neighbors)
            else:
                return neighbors
        elif isinstance(cp, pynt.elements.SwitchMatrix):
            return cp.getInterfaces()
        elif isinstance(cp, pynt.elements.Device):
            return cp.getNativeInterfaces()
        elif isinstance(cp, pynt.elements.BroadcastSegment):
            neighbors = []
            for intf in cp.getConnectedInterfaces():
                if cp in intf.getConnectedInterfaces():
                    neighbors.append(intf)
            if self.subjects:
                return filter(lambda x:x.getNamespace() in self.subjects, neighbors)
            else:
                return neighbors
        # if self.subjects:
        #     return filter(lambda x:x.getNamespace() in self.subjects, neighbors)

    def getRestrictedGraph(self, bandwidth=None):
        result = []
        if isinstance(self.sourcecp, pynt.elements.Device):
            devs = self.sourcecp.getDomain().getDevices()
        elif isinstance(self.sourcecp, pynt.elements.Interface):
            devs = self.sourcecp.getDevice().getDomain().getDevices()
        else:
            raise Exception("Unknown type of source found: %s (%s)" % (self.sourcecp,type(self.sourcecp)))
        for dev in devs:
            result += dev.getNativeInterfaces()
        return result
            
    def extractMin(self, unvisited, dist):
        # Sort the unvisited list based on the distances defined in dist.
        def customcmp(x,y):
            if dist[x] == dist[y]:          return 0 # this also catches both infinity values
            if dist[x] == infinity: return 1
            if dist[y] == infinity: return -1
            # no more infinities left, so we fall back to regular cmp
            return cmp(dist[x],dist[y])
        unvisited.sort(customcmp)
        logging.getLogger("pynt.output").debug("ExtractMin Returning %s" % unvisited[0])
        return unvisited.pop(0)
    
    def getMetric(self, source, target, bandwidth=None):
        metric = 0
        if bandwidth:
            if hasattr(source, "getAvailableCapacity") and source.getAvailableCapacity() < bandwidth:
                return infinity
            if hasattr(target, "getAvailableCapacity") and target.getAvailableCapacity() < bandwidth:
                return infinity
        metric += self._getMetric(source)
        metric += self._getMetric(target)
        return metric

    def _getMetric(self, obj):
        if isinstance(obj, pynt.elements.Interface) and obj.getMetric():
            return obj.getMetric()
        elif isinstance(obj, pynt.elements.Device):
            # Prefer SwitchingMatrices over Devices
            return 2
        else:
            return 1
        

    def findShortestPath(self, startid=None, endid=None, bandwidth=None):
        if self.intraDomain:
            self.restrictedGraph = self.getRestrictedGraph()
        if startid:
            self.sourcecp = pynt.xmlns.GetRDFObject(startid)
        if endid:
            self.destinationcp = pynt.xmlns.GetRDFObject(endid)
        q = [(0, self.sourcecp, ())]
        visited = set()
        while q:
            (cost, v1, path) = heapq.heappop(q)
            if v1 not in visited:
                visited.add(v1)
                path += (v1,)
                if v1 == self.destinationcp:
                    return list(path)
                for v2 in self.getNeighbors(v1):
                    if v2 not in visited:
                        m = self.getMetric(v1,v2,bandwidth)
                        if not m == infinity:
                            heapq.heappush(q, (cost+m, v2, path))
        return None
    
class DijkstraAbstract(Dijkstra):
    """Dijkstra pathfinding on a fully abstracted inter-domain graph.
    
    Each domain is collapsed onto a single 'Device'. The interfaces of this
    'device' are the interfaces with inter-domain connections."""
    def getGraph(self, bandwidth=None):
        result = []
        for dom in pynt.xmlns.GetAllRDFObjects(klass=pynt.elements.Domain):
            result.append(dom)
            result += dom.getInterfaces()
        result += [self.sourcecp, self.destinationcp]
        return result
    def getNeighbors(self, cp):
        # bootstrap finish and start
        if cp == self.destinationcp.getDomain():
            return [self.destinationcp]
        elif isinstance(cp, pynt.elements.Device):
            return [cp.getDomain()]
        elif isinstance(cp, pynt.elements.Interface):
            return [cp.getConnectedInterfaces()[0], cp.getDevice().getDomain()]
        elif isinstance(cp, pynt.elements.AdminDomain):
            return cp.getInterfaces()
        else:
            raise Exception

class DijkstraStar(Dijkstra):
    """Dijkstra pathfinding on a star inter-domain graph.

    Each domain is represented as a star, with the edge devices at the points, and a
    Domain object in the middle, connecting all the edges. A connection from the point
    to the center is only created if there are intra-domain interfaces with sufficient
    bandwidth.
    """

    def __init__(self,outfile=sys.stdout, subject=None,bandwidth=None):
        self.graph = None
        self.bandwidth = bandwidth
        Dijkstra.__init__(self,outfile,subject)

    def setGraph(self, graph):
        self.graph = graph
    def getGraph(self):
        return self.graph

    def generateGraph(self, bandwidth=None):
        self.graph = StarGraph()
        for dom in pynt.xmlns.GetAllRDFObjects(klass=pynt.elements.AdminDomain):
            # Get all devices that have an external interface
            for intf in dom.getInterfaces():
                if intf.getAvailableCapacity() >= bandwidth:
                    self.graph.addEdgeInterface(dom,intf,bandwidth)
        return self.graph

    def addEndpoints(self):
        if not self.graph:
            raise Exception("Cannot add endpoints if no graph is defined.")
        for endp in (self.sourcecp,self.destinationcp):
            self.graph.addDevice(endp)

    def initNeighbors(self, bandwidth=None):
        # if not self.graph:
        self.generateGraph(bandwidth)
        self.addEndpoints()

    def getNeighbors(self, cp):
        if isinstance(cp, pynt.elements.Interface):
            return [cp.getConnectedInterfaces()[0], cp.getDevice()]
        elif isinstance(cp, pynt.elements.Device):
            # An edge-node only has a connection to the domain if it has available 
            # internal bandwidth.
            result = self.graph.getInterdomInterfaces(cp)
            for intf in cp.getLogicalInterfaces():
                if intf in result:
                    # This is an inter-domain interface we already have
                    continue
                if intf.getAvailableCapacity() >= self.bandwidth:
                    # This is an internal interface, which has available bandwidth,
                    # so we have a connection to the domain.
                    result.append(cp.getDomain())
                    break
            return result
        elif isinstance(cp, pynt.elements.AdminDomain):
            return self.graph.getDomainDevices(cp)

    def findShortestPath(self, startid=None, endid=None, bandwidth=None):
        self.initNeighbors(bandwidth)
        result = Dijkstra.findShortestPath(self,startid,endid,bandwidth)
        for endp in [self.sourcecp,self.destinationcp]:
            self.graph.removeDevice(endp)
        return result

class DijkstraSemiAbstract(Dijkstra):
    """Dijkstra pathfinding on a semi-abstracted inter-domain graph.
    
    Each domain is represented as its edge-devices, with their inter-domain
    interfaces. Intra-domain connections are represented as connections between
    devices. Thehese connections only exist if a valid path can be found when
    we start pathfinding.
    """
    
    def __init__(self,outfile=sys.stdout, subject=None,bandwidth=None):
        self.graph = None
        self.bandwidth = bandwidth
        Dijkstra.__init__(self,outfile,subject)

    def generateGraph(self, bandwidth=None):
        self.graph = SemiAbstractGraph()
        for dom in pynt.xmlns.GetAllRDFObjects(klass=pynt.elements.AdminDomain):
            # Get all devices that have an external interface
            for intf in dom.getInterfaces():
                if intf.getAvailableCapacity() >= bandwidth:
                    dev = intf.getDevice()
                    self.graph.addDomainDevice(dom,dev)
                # Initialize the neighbor dict, this lists all intradomain devs that we can reach
                # Note that we explicitly do not check if these paths overlap!
                # We also want to add the source and target to that list if they are in the domain
                algorithm = Dijkstra(outfile=None, subject=dom.getNamespace())
                for dev in self.graph.getDomainDevices(dom):
                    self.graph.intraDomNeighbors[dev] = []
                    # Initialize the neighborlist with our own inter-domain interfaces
                    for intf in dev.getLogicalInterfaces():
                        if intf in dev.getDomain().getInterfaces():
                            self.graph.intraDomNeighbors[dev].append(intf)
                for dev in self.graph.getDomainDevices(dom):
                    for trg in self.graph.getDomainDevices(dom):
                        if (dev is trg) or (trg in self.graph.intraDomNeighbors[dev]) :
                            continue
                        algorithm.setEndpoints(dev, trg)
                        if algorithm.findShortestPath(bandwidth=bandwidth):
                            self.graph.intraDomNeighbors[dev].append(trg)
                            self.graph.intraDomNeighbors[trg].append(dev)
        return self.graph
    
    def addEndpoints(self):
        if not self.graph:
            raise Exception("Cannot add endpoints if no graph is defined.")
        for endp in (self.sourcecp,self.destinationcp):
            self.graph.addDevice(endp,self.bandwidth)
    
    def setGraph(self, graph):
        self.graph = graph
    def getGraph(self):
        return self.graph

    def initNeighbors(self, bandwidth=None):
        if not self.graph:
            self.generateGraph(bandwidth)
        self.addEndpoints()

    def getNeighbors(self, cp):
        if isinstance(cp, pynt.elements.Interface):
            return [cp.getConnectedInterfaces()[0], cp.getDevice()]
        elif isinstance(cp, pynt.elements.Device):
            return self.graph.intraDomNeighbors[cp]
    
    def findShortestPath(self, startid=None, endid=None, bandwidth=None):
        self.initNeighbors(bandwidth)
        result = Dijkstra.findShortestPath(self,startid,endid,bandwidth)
        for endp in [self.sourcecp,self.destinationcp]:
            self.graph.removeDevice(endp)
        return result
    
    def findShortestPathOld(self, startid=None, endid=None, bandwidth=None):
        return Dijkstra.findShortestPathOld(self, startid, endid, bandwidth)

class StarGraph(object):
    """Object to represent the StarGraph"""
    def __init__(self, domains = {}):
        self.domains = domains
        self.interDomainInterfaces = {}
        
    def addEdgeInterface(self, domain, interface, bandwidth):
        device = interface.getDevice()
        # We only add the edge device to the graph if it has any other capacity.
        for i in device.getLogicalInterfaces():
            if i == interface:
                continue
            if i.getAvailableCapacity() >= bandwidth:
                self.addInterDomainInterface(device,interface)

    def addInterDomainInterface(self,device,interface):
        domain = device.getDomain()
        if self.domains.has_key(domain):
            if device not in self.domains[domain]:
                self.domains[domain].append(device)
        else:
            self.domains[domain] = [device]
        if not self.interDomainInterfaces.has_key(device):
            self.interDomainInterfaces[device] = [interface]
        elif interface not in self.interDomainInterfaces[device]:
            self.interDomainInterfaces[device].append(interface)

    def addDevice(self, device):
        # Add the device to its domain
        if device not in self.domains[device.getDomain()]:
            self.domains[device.getDomain()].append(device)
        if not self.interDomainInterfaces.has_key(device):
            self.interDomainInterfaces[device] = []
        
    def getInterdomInterfaces(self,device):
        try:
            result = self.interDomainInterfaces[device]
        except KeyError:
            result = []
        return result
        
    def getDomainDevices(self,domain):
        return self.domains[domain]
    
    def removeDevice(self,device):
        # First check if this is not an inter-domain device we should keep
        for intf in device.getLogicalInterfaces():
            if intf.getConnectedInterfaces():
                if device.getDomain() != intf.getConnectedInterfaces()[0].getDevice().getDomain():
                    return
        # Remove it from the devices in the domain
        self.domains[device.getDomain()].remove(device)
        self.interDomainInterfaces.pop(device)
        
        
class SemiAbstractGraph(object):
    def __init__(self,domains={},intraDomNeighbors={}):
        self.domains = domains
        self.intraDomNeighbors = intraDomNeighbors
    
    def addDomainDevice(self,domain,device):
        if self.domains.has_key(domain):
            if device not in self.domains[domain]:
                self.domains[domain].append(device)
        else:
            self.domains[domain] = [device]
        
    def getDomainDevices(self,domain):
        return self.domains[domain]
    
    def getIntraDomainNeighbors(self,device):
        return self.intraDomNeighbors[device]

    def addDevice(self,device,bandwidth):
        # Add the device to its domain
        if device not in self.domains[device.getDomain()]:
            self.domains[device.getDomain()].append(device)
        # Add intra-domain neighbors where needed.
        if not self.intraDomNeighbors.has_key(device):
            self.intraDomNeighbors[device] = []
            algorithm = Dijkstra(outfile=None, subject=device.getDomain().getNamespace())
            for domdev in self.getDomainDevices(device.getDomain()):
                if domdev is device:
                    continue
                algorithm.setEndpoints(domdev, device)
                if algorithm.findShortestPath(bandwidth=bandwidth):
                    self.intraDomNeighbors[domdev].append(device)
                    self.intraDomNeighbors[device].append(domdev)
        
    def removeDevice(self,device):
        # First check if this is not an inter-domain device we should keep
        for intf in device.getLogicalInterfaces():
            if intf.getConnectedInterfaces():
                if device.getDomain() != intf.getConnectedInterfaces()[0].getDevice().getDomain():
                    return
        # Remove it from the devices in the domain
        self.domains[device.getDomain()].remove(device)
        # Remove its entry in the intraDomNeighbors
        self.intraDomNeighbors.pop(device)
        # Remove all occurences in other neighbors entries
        for domdev in self.domains[device.getDomain()]:
            if device in self.intraDomNeighbors[domdev]:
                self.intraDomNeighbors[domdev].remove(device)
        
class DijkstraEROSolutionPrinter(pynt.output.BaseOutput):
    def __init__(self, outfile=None, subject=None, atomic=True):
        pynt.output.BaseOutput.__init__(self, outfile, subject, atomic)
        self.resultString = ""
    def printSolutions(self, solution):
        print solution
        
class DijkstraDotSolutionPrinter(pynt.output.dot.DeviceGraphOutput):
    count = 0
    path  = None
    color = "#ffffff"

    def __init__(self, outfile=None, subject=None, atomic=True):
        pynt.output.dot.DeviceGraphOutput.__init__(self, outfile, subject, atomic)
        self.resultString = ""

    def write(self, string):
        self.resultString += (self.indent*'    ')+str(string)+"\n"

    def printFooter(self):
        pynt.output.dot.DeviceGraphOutput.printFooter(self)
        self.outfile.write(self.resultString)

    def inPath(self, interface1, interface2, connectiontype):
        """Return True if the connection from interface1 to interface2 is part of self.path"""
        if (not self.path) or (len(self.path) <= 1):
            return False
        for hop in range(1,len(self.path)):
            if (self.path[hop-1].cp == interface1) and \
                    (self.path[hop].cp == interface2) and \
                    isinstance(self.path[hop].prevconnection, connectiontype):
                return True
        return False
    
    def printSolutions(self, solution):
        """This is an adapted version of output() to also print the solution before closing the file."""
        logger = logging.getLogger("pynt.output")
        logger.log(25, "Writing %s to %s" % (type(self).__name__, self.filename))
        if not self.outfile:
            self.openfile()
        self.printHeader()
        self.printDocumentMetaData(self.subject)
        self.printElement(self.subject)
        # Begin difference
        self.color = "#00ff00"
        if solution:
            # Make a copy before we destroy the thing
            solution = solution[:]
            endpoint = solution.pop()
            endpointcp = None
            if isinstance(endpoint, pynt.elements.Interface):
                endpointcp = endpoint
                endpoint = endpoint.getDevice()
        while solution:
            prev = solution.pop()
            prevcp = None
            if isinstance(prev, pynt.elements.Interface):
                prevcp = prev
                prev = prev.getDevice()
            self.write('"%s" -- "%s" [color="%s" %s];' % (prev.getName(), endpoint.getName(),
               self.color, self._extraProperties(prev, prevcp , endpoint,endpointcp)))
            endpoint = prev
            endpointcp = prevcp
        # End difference
        self.printFooter()
        self.closefile()
        
    def _extraProperties(self, prev, prevcp, endpoint, endpointcp):
        result = ""
        if prevcp:
            result += ', taillabel="%s"' % prevcp.getName()
        if endpointcp:
            result += ', headlabel="%s"' % endpointcp.getName()
        result += ', style="setlinewidth(%s)"' % self.metricToLineWidth(prevcp, endpointcp)
        return result
