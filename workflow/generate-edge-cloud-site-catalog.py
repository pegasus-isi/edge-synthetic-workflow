#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from Pegasus.api import *

WORK_DIR = Path(__file__).parent.resolve()
LOCAL_STORAGE_DIR = str(WORK_DIR / "wf-output")
LOCAL_SCRATCH_DIR = str(WORK_DIR / "wf-scratch")

sc = SiteCatalog()

local = Site("local")

local_storage = Directory(Directory.LOCAL_STORAGE, LOCAL_STORAGE_DIR)
local_storage.add_file_servers(FileServer("file://" + LOCAL_STORAGE_DIR, Operation.ALL))
local_scratch = Directory(Directory.SHARED_SCRATCH, LOCAL_SCRATCH_DIR)
local_scratch.add_file_servers(FileServer("file://" + LOCAL_SCRATCH_DIR, Operation.ALL))
local.add_directories(local_storage, local_scratch)
local.add_pegasus_profile(SSH_PRIVATE_KEY="/home/panorama/.ssh/storage_key")
local.add_env(PEGASUS_MULTIPART_DIR=str(WORK_DIR / "pegasus.multipart.dir"))

condorpool = Site("condorpool")
condorpool.add_pegasus_profile(style="condor")
condorpool.add_condor_profile(universe="vanilla")


staging = Site("staging")
staging_dir = Directory(Directory.SHARED_SCRATCH, "/home/panorama/public_html")
staging_dir.add_file_servers(
            FileServer("http://10.100.101.107/~panorama/", Operation.GET),
            FileServer("scp://panorama@10.100.101.107/home/panorama/public_html/", Operation.PUT)
        )
staging.add_directories(staging_dir)


sc.add_sites(local, condorpool, staging)
sc.write(sys.stdout)
sc.write()


