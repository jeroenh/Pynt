# -*- coding: utf-8 -*-
"""Printer classes for the algoritm. Each printer class sends output of the algorithm to the user, or to a file.
After a printer class is instantiated, it is typically added to an algoritm instance. While running, 
the algorithm instance then calls one of the 5 methods of the printer class."""

# standard modules
import sys
import time
import os.path


class ProgressPrinter(object):
    def __init__(self, stream=sys.stdout):
        self.stream = stream
    def printProgressHeader(self):
        pass
    def printProgress(self, count, path, leaves, note):
        pass
    def printProgressFooter(self):
        pass
    def printSolutions(self, paths):
        for path in paths:
            self.printSolution(path)
    def printSolution(self, path):
        pass

NoPrinter = ProgressPrinter

class ResultTextPrinter(ProgressPrinter):
    def printSolution(self, path):
        path.prettyprint()

class SimpleTextProgressPrinter(ResultTextPrinter):
    def printProgress(self, count, path, leaves, note):
        #self.stream.write("%7d.%6.2f  %2d  %4d\n" % (count, path.getMetric(), len(path), len(leaves)))
        self.stream.write(".")
    def printProgressFooter(self):
        self.stream.write("\n")

class TextProgressPrinter(ResultTextPrinter):
    namespaces      = None  # List of involved namespaces
    sourcecp        = None  # source interface
    destinationcp   = None  # destination interface
    progressfile    = None  # filename of .dot progress file
    def __init__(self, stream=sys.stdout):
        self.stream = stream
    def printProgressHeader(self):
        self.stream.write("Try  Hops Metric StackId Outer Leave Tree size\n")
        self.stream.write("---- ---- ------ ------- ----------- ---------------------------------------------\n")
    def printProgress(self, count, path, leaves, note):
        cp = path.getLastHop().getConnectionPoint()
        if cp.getDevice():
            cpname = "%-11s %-10s" % (cp.getDevice().getName(), cp.getName())
        else:
            cpname = "%-11s %-10s" % ("", cp.getName())
        self.stream.write("%4d %4d %6.2f %s %d %s%s\n" % (count, len(path), path.getMetric(), cpname, len(leaves), len(leaves)*'.', note))
        pass
    def printSolutions(self, paths):
        self.stream.write("%d SOLUTION: " % len(paths))
        ProgressPrinter.printSolutions(self, paths)



class SingleFilePrinter(ProgressPrinter):
    """Print the final solution to a output file. output is a pynt.output.BaseOutput class."""
    def __init__(self, output, outputRDFobjects=None):
        self.outputRDFobjects = outputRDFobjects
        self.myout = output
    def printProgress(self, count, path, leaves, note):
        self.myout.count = count
    def printSolution(self, path):
        self.myout.path  = path
        self.myout.color = "#00ff00"
        self.myout.output(self.outputRDFobjects)
    

class OverwriteFilePrinter(SingleFilePrinter):
    """Repeatedly print output to the same file. output is a pynt.output.BaseOutput class.
    Typical use is a dot file, which is written over and over again. GraphViz on Mac OS X will 
    dynamically update the graph."""
    def __init__(self, output, outputRDFobjects=None, frequency=1):
        self.outputRDFobjects = outputRDFobjects
        self.myout = output
        self.myout.output(self.outputRDFobjects)
        self.myout.count = 0
        self.myout.color = "#ff0000"
        self.frequency = frequency
    def printProgress(self, count, path, leaves, note):
        if (count % self.frequency == 0):
            self.myout.path  = path
            self.myout.count = count
            self.myout.output(self.outputRDFobjects)
        # time.sleep(0.5)
    def printSolution(self, path):
        self.myout.path  = path
        # self.myout.count = "9999"
        self.myout.color = "#00ff00"
        self.myout.output(self.outputRDFobjects)
    


class MultiFilePrinter(SingleFilePrinter):
    """For each step, print output to a new file. output is a pynt.output.BaseOutput class.
    Typical use is a dot file, where the sequence is later used to make a movie of the sequence."""
    def __init__(self, output, outputRDFobjects=None, frequency=1):
        self.outputRDFobjects = outputRDFobjects
        self.myout = output
        (self.filebasename, self.fileext) = os.path.splitext(output.filename)
        self.myout.count = 0
        self.myout.color = "#ff0000"
        self.frequency = frequency
    def printProgress(self, count, path, leaves, note):
        if (count % self.frequency == 0):
            filename = self.getFileName(count)
            self.myout.setOutputFile(filename)
            self.myout.path  = path
            self.myout.count = count
            self.myout.output(self.outputRDFobjects)
    def printSolution(self, path):
        self.myout.count += 1
        filename = self.getFileName(self.myout.count)
        self.myout.setOutputFile(filename)
        self.myout.path  = path
        self.myout.color = "#00ff00"
        self.myout.output(self.outputRDFobjects)
    def getFileName(self, count):
        return self.filebasename + ("%04d" % count) + self.fileext
    

defaultProgressPrinter = SimpleTextProgressPrinter

