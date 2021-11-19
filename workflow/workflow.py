#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path
from typing import List

import yaml
from Pegasus.api import *

logging.basicConfig(level=logging.DEBUG)

def parse_args(args: List[str] = sys.argv[1:]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic workflow")

    parser.add_argument(
                "--pegasus-keg-path",
                required=True,
                type=str,
                help="Absolute path to pegasus-keg" 
            )

    parser.add_argument(
                "--height",
                required=True,
                type=int,
                choices=range(2,101),
                metavar="[2,100]",
                help="Number of levels of jobs, vertically (critical path with be height number of jobs)"
            )

    parser.add_argument(
                "--runtime",
                required=True,
                type=int,
                nargs="+",
                choices=range(1,301),
                metavar="[1,300]",
                help=" ".join(("Runtime of the jobs in seconds at each level. The ith value will",
                      "apply to all jobs on the ith level.",
                      "The last value entered will set the runtime for the current",
                      "level and all subsequent levels. For example, if '--runtime 1 2 3'",
                      "is set, then jobs at the 3rd and subsequent levels will have a",
                      "runtime of 3 seconds implemented as a spin lock."
                    ))
            )

    parser.add_argument(
                "--output-sizes",
                required=True,
                type=int,
                nargs="+",
                choices=range(1,900001),
                metavar="[1,90000]",
                help=" ".join(("Output file sizes of each job at each level in MB.",
                        "The ith value will apply to the output files of all jobs",
                        "at the ith level. The last value entered will set the output",
                        "file size for jobs of the current and all subsequent levels.",
                        "For example, if '--output-sizes 10 20 30' is set, then jobs",
                        "at the 3rd and subsequent levels will have output 30MB output files."
                    ))
            )

    parser.add_argument(
                "--replica-catalog",
                required=True,
                type=str,
                default=None,
                help=" ".join(("Absolute path to replica catalog.",
                        "A workflow job will be created for each initial input file.",
                        "The number of entries in the workflow catalog will determine",
                        "the width of the workflow."
                    ))
            )

    parser.add_argument(
                "--job-mapping",
                action="store_true",
                default=False,
                help="Use job-machine-mapping.yml to see what jobs to map to which machines"
            )

    parser.add_argument(
                "-p",
                "--plot",
                type=str,
                choices=["pdf", "png"],
                default=None,
                help="Generate workflow diagram as workflow.<pdf | png>"
            )

    parser.add_argument(
                "-s",
                "--submit",
                default=False,
                action="store_true",
                help="Submit the workflow"
            )

    return parser.parse_args(args)

if __name__=="__main__":
    args = parse_args()

    # check for replica catalog
    REPLICAS = dict()
    if args.replica_catalog:
        replica_catalog_path =  Path(args.replica_catalog)
        assert replica_catalog_path.exists()

        with replica_catalog_path.open("r") as f:
            rc = yaml.load(f, Loader=yaml.Loader)
            for input_file in rc["replicas"]:
                assert len(input_file["pfns"]) == 1
                REPLICAS[input_file["lfn"]] = input_file["pfns"][0]

    # check for job mapping file
    JOB_MAPPINGS = None
    if args.job_mapping:
        JOB_MAPPING_FILE = Path("job-machine-mapping.yml")
        assert JOB_MAPPING_FILE.exists()
        with JOB_MAPPING_FILE.open("r") as f:
            JOB_MAPPINGS = yaml.load(f, Loader=yaml.Loader)

    ### Properties ############################################################
    props = Properties()
    # not concerned about failures, will stick to dev mode
    props["pegasus.mode"] = "development" 
    props["pegasus.data.configuration"] = "nonsharedfs"
    props["pegasus.monitord.encoding"] = "json"
    props["pegasus.catalog.workflow.amqp.url"] = "amqp://friend:donatedata@msgs.pegasus.isi.edu:5672/prod/workflows"
    props.write()

    ### Transformations #######################################################
    tc = TransformationCatalog()
    keg = Transformation(
                "keg",
                site="local",
                pfn=args.pegasus_keg_path,
                is_stageable=True,
            )

    tc.add_transformations(keg)
    tc.write()

    ### Workflow ##############################################################
    wf = Workflow("edge-workflow")

    current_output_file_size_idx = 0
    current_runtime_idx = 0
    output_file_size = None
    runtime = None

    for level in range(1, args.height):
        jobs_per_level = list()

        output_file_size = args.output_sizes[current_output_file_size_idx]
        runtime = args.runtime[current_runtime_idx]

        for col, lfn in enumerate(REPLICAS, start=1):
            job_id = "{}_{}".format(level,col)
            output_file_name = "{}.txt".format(job_id)

            j = Job(keg, _id=job_id)\
                    .add_outputs(output_file_name, stage_out=False)

            wf.add_jobs(j)

            if level == 1:
                j.add_inputs(lfn)\
                    .add_args("-T", runtime, "-i", lfn, "-o", "{}={}M".format(output_file_name, output_file_size))
            else:
                input_file = "{}_{}.txt".format(level-1,col)
                j.add_inputs(input_file)\
                    .add_args("-T", runtime, "-i", input_file, "-o", "{}={}M".format(output_file_name, output_file_size))\

        if current_output_file_size_idx != len(args.output_sizes) - 1:
            current_output_file_size_idx += 1
            output_file_size = args.output_sizes[current_output_file_size_idx]

        if current_runtime_idx != len(args.runtime) - 1:
            current_runtime_idx += 1
            runtime = args.runtime[current_runtime_idx]

    merge_job = Job(keg, _id="merge")\
                    .add_args("-T", runtime, "-o", "merge.txt={}M".format(output_file_size))\
                    .add_inputs(*["{}_{}.txt".format(args.height-1, i) for i in range(1, len(REPLICAS)+1)])\
                    .add_outputs("merge.txt", stage_out=True)
    wf.add_jobs(merge_job)

    # map jobs to machines
    if JOB_MAPPINGS:
        for job_id, machine_id in JOB_MAPPINGS.items():
            print(job_id)
            if job_id in wf.jobs:
                wf.jobs[job_id].add_condor_profile(requirements="MACHINE_SPECIAL_ID == {}".format(machine_id))
            else:
                raise RuntimeError("job id: {} not found in workflow when trying to assign to machine".format(
                    job_id))

    wf.write()
    
    if args.plot:
        wf.graph(include_files=True, no_simplify=True, label="xform-id", output="workflow.png")

    if args.submit:
        wf.plan(
                output_site="local",
                sites=["condorpool"],
                staging_sitse={"condorpool": "staging"},
                force=True,
                submit=True
            )





          
    

