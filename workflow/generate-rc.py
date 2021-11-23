#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List
from Pegasus.api import *

def parse_args(args: List[str] = sys.argv[1:]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="generate rc....")
    parser.add_argument(
        "--compute-on-edge",
        default=False,
        action="store_true",
        help="Sets pfns to file paths instead of http urls as we will symlink (initial jobs will run on edge so no need to pull inputs over http)"
    )

    return parser.parse_args(args)

if __name__=="__main__":
    args = parse_args()

    rc = ReplicaCatalog()

    NUM_INPUT_FILES = 8

    for i in range(1, NUM_INPUT_FILES+1):
        lfn="test{}.txt".format(i)

        pfn = None
        site = None
        if args.compute_on_edge:
            site = "condorpool"
            pfn = "/home/panorama/public_html/test-data/{}".format(lfn)
        else:
            site = "edge"
            pfn = "http://10.100.100.109/~panorama/test-data/{}".format(lfn)
        
        rc.add_replica(site=site, lfn=lfn, pfn=pfn)
    
    rc.write(sys.stdout)
    rc.write()

