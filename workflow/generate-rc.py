#!/usr/bin/env python3
from pathlib import Path
from Pegasus.api import *

rc = ReplicaCatalog()

'''
for f in Path("./inputs").iterdir():
    if f.name.endswith(".txt"):
        rc.add_replica(site="local", lfn=f.name, pfn=f.resolve())
'''
for i in range(1,3):
    rc.add_replica(
                site="edge", 
                lfn="test{}.txt".format(i), 
                pfn="http://10.100.100.109/~panorama/test-data/test{}.txt".format(i)
        )

rc.write()
