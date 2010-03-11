#!/usr/bin/env python
# -*- coding: utf-8 -*-

# local modules
try:
    import pynt
except ImportError:
    raise ImportError("Package pynt is not available. Copy pynt to python/site-packages, or set $PYTHONPATH\n")
import pynt.input.commandline
import pynt.input.glimmerglass


if __name__=="__main__":
    # pynt.input.commandline.DeviceMain parses the sys.arg; the given values are the compulsory default values
    pynt.input.commandline.DeviceMain(
            fetcherclass=pynt.input.glimmerglass.OXCFetcher, 
            hostname='speculaas.uva.netherlight.nl'
        )

