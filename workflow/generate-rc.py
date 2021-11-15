#!/usr/bin/env python3
from pathlib import Path
from Pegasus.api import *

rc = ReplicaCatalog()

for f in Path("./inputs").iterdir():
    if f.name.endswith(".txt"):
        rc.add_replica(site="local", lfn=f.name, pfn=f.resolve())

rc.write()
