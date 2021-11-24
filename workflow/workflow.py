#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path
from typing import List

import yaml
from Pegasus.api import *

logging.basicConfig(level=logging.INFO)

def parse_args(args: List[str] = sys.argv[1:]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="".join(("Synthetic workflow. Jobs assigned to the edge (MACHINE_SPECIAL_ID=1) ",
            "will incur a 33% runtime slowdown as a penalty to represent lower powered edge devices."
        )))

    parser.add_argument(
                "--workflow-name",
                required=True,
                type=str,
                help="Name of the workflow"
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
        "--edge-only",
        default=False,
        action="store_true",
        help="Do not set staging_sites in wf.plan for edge only scenario AND set pegasus.transfer.links=True in properties. Also set all jobs to run on MACHINE_SPECIAL_ID=1"
    )

    parser.add_argument(
        "--cloud-only",
        default=False,
        action="store_true",
        help="Set all jobs to run on MACHINE_SPECIAL_ID=0"
    )

    parser.add_argument(
        "--map-top-level-to-edge",
        default=False,
        action="store_true",
        help="Map all top level jobs to edge device(s) with MACHINE_SPECIAL_ID=1"
    )

    parser.add_argument(
                "-s",
                "--submit",
                default=False,
                action="store_true",
                help="Submit the workflow"
            )

    parser.add_argument(
                "-p",
                "--plot",
                type=str,
                choices=["pdf", "png"],
                default=None,
                help="Generate workflow diagram as workflow.<pdf | png>"
            )

    return parser.parse_args(args)

if __name__=="__main__":
    args = parse_args()

    # replica catalog
    REPLICAS = dict()
    rc_path = Path("./replicas.yml")
    assert rc_path.exists()

    with rc_path.open("r") as f:
        rc = yaml.load(f, Loader=yaml.Loader)
        for input_file in rc["replicas"]:
            assert len(input_file["pfns"]) == 1
            REPLICAS[input_file["lfn"]] = input_file["pfns"][0]

    ### Properties ############################################################
    props = Properties()
    # not concerned about failures, will stick to dev mode
    props["pegasus.mode"] = "development" 
    props["pegasus.integrity.checking"] = "none"
    props["pegasus.data.configuration"] = "nonsharedfs"
    props["pegasus.transfer.bypass.input.staging"] = "True"
    props["pegasus.monitord.encoding"] = "json"
    props["pegasus.catalog.workflow.amqp.url"] = "amqp://friend:donatedata@msgs.pegasus.isi.edu:5672/prod/workflows"

    if args.edge_only:
        props["pegasus.transfer.links"] = "True"

    props.write()

    ### Transformations #######################################################
    tc = TransformationCatalog()
    keg = Transformation(
                "keg",
                site="condorpool",
                pfn="/usr/bin/pegasus-keg",
                is_stageable=False,
            )

    tc.add_transformations(keg)
    tc.write()

    ### Workflow ##############################################################
    wf = Workflow(args.workflow_name)

    current_output_file_size_idx = 0
    current_runtime_idx = 0
    output_file_size = None
    runtime = None

    def apply_runtime_penalty(runtime: int, penalty: float = 0.33333) -> int:
        """Apply penalty to runtime"""
        return int(runtime + (runtime * penalty))

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
            j.add_inputs(lfn)

            if level == 1:

                if args.map_top_level_to_edge or args.edge_only:
                    j.add_condor_profile(requirements="MACHINE_SPECIAL_ID == 1")\
                        .add_args("-T", apply_runtime_penalty(runtime), "-i", lfn, "-o", "{}={}M".format(output_file_name, output_file_size))
                elif args.cloud_only:
                    j.add_condor_profile(requirements="MACHINE_SPECIAL_ID == 0")\
                        .add_args("-T", runtime, "-i", lfn, "-o", "{}={}M".format(output_file_name, output_file_size))

            else:
                input_file = "{}_{}.txt".format(level-1,col)
                j.add_inputs(input_file)
                
                if args.edge_only:
                    j.add_condor_profile(requirements="MACHINE_SPECIAL_ID == 1")\
                        .add_args("-T", apply_runtime_penalty(runtime), "-i", input_file, "-o", "{}={}M".format(output_file_name, output_file_size))
                else:
                    j.add_condor_profile(requirements="MACHINE_SPECIAL_ID == 0")\
                        .add_args("-T", runtime, "-i", input_file, "-o", "{}={}M".format(output_file_name, output_file_size))

        if current_output_file_size_idx != len(args.output_sizes) - 1:
            current_output_file_size_idx += 1
            output_file_size = args.output_sizes[current_output_file_size_idx]

        if current_runtime_idx != len(args.runtime) - 1:
            current_runtime_idx += 1
            runtime = args.runtime[current_runtime_idx]

    merge_job = Job(keg, _id="merge")\
                    .add_inputs(*["{}_{}.txt".format(args.height-1, i) for i in range(1, len(REPLICAS)+1)])\
                    .add_outputs("merge.txt", stage_out=True)

    if args.edge_only:
        merge_job.add_condor_profile(requirements="MACHINE_SPECIAL_ID == 1")\
                    .add_args("-T", apply_runtime_penalty(runtime), "-o", "merge.txt={}M".format(output_file_size))
    else:
        merge_job.add_condor_profile(requirements="MACHINE_SPECIAL_ID == 0")\
                    .add_args("-T", runtime, "-o", "merge.txt={}M".format(output_file_size))\

    
    wf.add_jobs(merge_job)
    wf.write()
    
    if args.plot:
        wf.graph(include_files=True, no_simplify=True, label="xform-id", output="workflow.png")

    if args.edge_only:
        wf.plan(
                output_site="local",
                sites=["condorpool"],
                force=True,
                submit=args.submit
            ).wait()
    else:
        wf.plan(
                output_site="local",
                sites=["condorpool"],
                staging_sites={"condorpool": "staging"},
                force=True,
                submit=args.submit
            ).wait()
       
    with open("submit_dir_path.txt", "w") as f:
        f.write(str(wf.braindump.submit_dir))

    





          
    

