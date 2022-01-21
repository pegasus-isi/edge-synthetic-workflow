#!/usr/bin/env python

import subprocess
import os
import json
from argparse import ArgumentParser

def read_compute_jobs(jobstate, submit_folder):
    compute_jobs = {}
    lines = []
    exceptions = ["INTERNAL", "create_dir_", "cleanup_", "stage_in_", "stage_out_"]
    accept_states = ["SUBMIT", "EXECUTE", "JOB_TERMINATED", "JOB_SUCCESS", "POST_SCRIPT_STARTED", "POST_SCRIPT_TERMINATED", "POST_SCRIPT_SUCCESS"]
    with open(jobstate, 'r') as f:
        lines = f.readlines()

    for line in lines:
        l = line.split()
        guard = False
        for e in exceptions:
            if e in l[1]:
                guard = True
                break
        if guard:
            continue

        if l[2] in accept_states:
            if l[1] in compute_jobs:
                compute_jobs[l[1]][l[2]] = int(l[0])
            else:
                compute_jobs[l[1]] = {l[2]: int(l[0])}

    for job in compute_jobs:
        kickstart_out = submit_folder + "/00/00/" + job + ".out.000"
        if not os.path.exists(kickstart_out):
            kickstart_out = submit_folder + "/00/01/" + job + ".out.000"
        hostname = subprocess.check_output(["grep", "-w", "hostname", kickstart_out]).split()[1].replace('"', '')
        if hostname.startswith("ccgrid-worker"):
            compute_jobs[job]["site"] = "CLOUD"
        else:
            compute_jobs[job]["site"] = "EDGE"

    print len(compute_jobs.keys())
    return compute_jobs

def print_condorpool_utilization_ensemble(submit_folder, outputfile):
    testcase_start = 10000000000
    testcase_end = 0
    workflows = {}

    #print submit_folder
    braindump = os.path.join(submit_folder, "braindump.yml")
    jobstate = os.path.join(submit_folder, "jobstate.log")

    dax_label = subprocess.check_output(["grep", "-w", "dax_label", braindump]).split()[1].replace('"', '')
    workflow_id = subprocess.check_output(["grep", "-w", "wf_uuid", braindump]).split()[1].replace('"', '')
    start_time = subprocess.check_output(["head", "-n 1", jobstate]).split()[0]
    end_time = subprocess.check_output(["tail", "-n 1", jobstate]).split()[0]

    testcase_start = min(testcase_start, int(start_time))
    testcase_end = max(testcase_end, int(end_time))

    compute_jobs = read_compute_jobs(jobstate, submit_folder)
    workflows[workflow_id] = {"start": int(start_time), "end": int(end_time), "jobs": compute_jobs}

    print "%s is done parsing" % submit_folder
    #print workflows.keys()

    #calculate condorpool usage perf 2 seconds
    condorpool_stats = []
    step = 1
    for t in xrange(testcase_start, testcase_end+1, step):
        edge_counter = 0
        cloud_counter = 0
        for wf in workflows:
            if t > workflows[wf]["start"] and t < workflows[wf]["end"]:
                for j in workflows[wf]["jobs"]:
                    job = workflows[wf]["jobs"][j]
                    if t >= job["EXECUTE"] and t <= job["JOB_SUCCESS"]:
                    #if t >= job["SUBMIT"] and t <= job["POST_SCRIPT_SUCCESS"]:
                    #if t >= job["EXECUTE"] and t <= job["POST_SCRIPT_SUCCESS"]:
                        if job["site"] == "EDGE":
                            edge_counter += 1
                        else:
                            cloud_counter += 1
        if edge_counter > 24:
            edge_counter = 24
        condorpool_stats.append([t - testcase_start, edge_counter, cloud_counter])
        
    f = open(outputfile, 'w')
    f.write("#{0},{1},{2},{3}\n".format("timestamp","edge_num_of_slots", "cloud_num_of_slots", "edge_counter_limit"))
    
    for point in condorpool_stats:
        f.write("{0},{1},{2},{3}\n".format(point[0], point[1], point[2], 24))
    f.close()

    return

def print_condorpool_utilization(log, prefix):   
    for conf in log:
        print conf
        outputfile = os.path.join(prefix, "orcasound-utilization-%s.dat" % (conf.lower()))
        print outputfile
        submit_folder = os.path.join("ORCA", conf+"-RUN04/panorama/pegasus/orcasound/run0001")
        print submit_folder
        print_condorpool_utilization_ensemble(submit_folder, outputfile)

if __name__ == "__main__":
    parser = ArgumentParser(description="Orca Workflow")
    args = parser.parse_args()

    if not os.path.isdir("statistics"):
        os.makedirs("statistics")

    run_log = ["CLOUD", "EDGE-CLOUD", "EDGE"]

    print_condorpool_utilization(run_log, "statistics")
