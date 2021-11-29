#!/usr/bin/env python3
import argparse
import pprint
import shlex
import sys
from pathlib import Path
from typing import List, Dict

import yaml

pp = pprint.PrettyPrinter(indent=4)

def parse_args(args: List[str] = sys.argv[1:]) -> argparse.Namespace:
    """Parse CLI arguments"""

    parser = argparse.ArgumentParser(description="submit dir parser....")
    parser.add_argument(
                "submit_dir",
                type=str,
                help="path to submit directory of interest"
            )

    parser.add_argument(
                "-o",
                "--output",
                type=str,
                default="data.yml",
                help="filename that data will be serialized (as yaml) to, defaults to data.yml"
            )
    
    args = parser.parse_args(args)
    args.submit_dir = Path(args.submit_dir)
    args.output = Path(args.output)
    
    assert args.submit_dir.exists()

    return args


def traverse_submit_dir(submit_dir_path: Path, data: Dict) -> None:
    """
    Traverse submit directory and build up data dict with all kickstart records
    and file transfer attempts.
    """

    def _traverse(dir: Path, data: Dict) -> None:
        for f in dir.iterdir():
            if not f.is_dir():
                if f.match("*.out.*"):
                    parse_job_files(f, data)
            else:
                _traverse(f, data)

    _traverse(submit_dir_path, data)


def parse_job_files(out_file: Path, data: Dict) -> None:
    """Parse *.out.*  and *.err.* files in submit directory"""
    entry = {
            "job": out_file.name.split(".")[0],
            "kickstart-record": None,
            "transfer-input": {
                    "output": None,
                    "num-transfered": None,
                    "amount-transfered": None,
                    "duration": None,
                    "rate": None,
                },
            "transfer-output": {
                    "output": None,
                    "num-transfered": None,
                    "amount-transfered": None,
                    "duration": None,
                    "rate": None,
                }
        }

    with out_file.open("r") as f:
        ks_record = list()
        multipart_header = "---------pegasus-multipart"
        for line in f:
            if multipart_header not in line:
                ks_record.append(line)
            else:
                break

    entry["kickstart-record"] = yaml.load("".join(ks_record), Loader=yaml.Loader)

    def get_xfer_stats(line: str) -> dict:
        tokens = shlex.split(line)
        return {
                "num-transfered": int(tokens[5]),
                "amount-transfered": tokens[7] + " " + tokens[8],
                "duration": tokens[11] + " " + tokens[12].replace(".", ""),
                "rate": tokens[14] + " " + tokens[15],
                "src-dst": None
            }

    def get_src_dst(line: str) -> str:
        tokens = shlex.split(line)
        return tokens[5]

    if "register_staging" not in out_file.name and\
            "cleanup_" not in out_file.name and\
            "clean_up_" not in out_file.name and\
            "create_dir" not in out_file.name and\
            "stage_out" not in out_file.name:
        err_file = Path(out_file.name.replace(".out.", ".err.")) 
        err_file = out_file.resolve().parent / err_file

        transfer_input = list()
        transfer_input_metrics = dict()

        transfer_output = list()
        transfer_output_metrics = dict()

        with err_file.open("r") as f:
            while True:
                l = f.readline()

                if "Staging in input data and executables" in l:
                    while True:
                        l = f.readline()
                        if "[Pegasus Lite] Executing the user task" in l:
                            break
                        
                        if "Stats: Total" in l:
                            transfer_input_metrics = get_xfer_stats(l)

                        if "Between sites" in l:
                            transfer_input_metrics["src-dst"] = get_src_dst(l)

                        transfer_input.append(l)

                if "Staging out output files" in l:
                    while "PegasusLite: " not in l:
                        l = f.readline()

                        if "Stats: Total" in l:
                            transfer_output_metrics = get_xfer_stats(l)

                        if "Between sites" in l:
                            transfer_output_metrics["src-dst"] = get_src_dst(l)

                        transfer_output.append(l)

                if l is None or l == "":
                    break
        
        entry["transfer-input"]["output"] = "\n".join(list(map(lambda s: s.strip(), transfer_input)))
        entry["transfer-input"].update(transfer_input_metrics)

        entry["transfer-output"]["output"] = "\n".join(list(map(lambda s: s.strip(), transfer_output)))
        entry["transfer-output"].update(transfer_output_metrics)

    if "stage_out" in out_file.name:
        stage_out_xfer_output = entry["kickstart-record"][0]["files"]["stdout"]["data"]
        transfer_output_metrics = None
        for l in stage_out_xfer_output.split("\n"):
            if "Stats: Total" in l:
                transfer_output_metrics = get_xfer_stats(l)
                break

        entry["transfer-output"]["output"] = stage_out_xfer_output
        entry["transfer-output"].update(transfer_output_metrics)


    def parse_ks_record(record) -> dict:
        duration = record[0]["duration"]
        transformation = record[0]["transformation"]
        executable = record[0]["mainjob"]["executable"]["file_name"]
        wf_label = record[0]["wf-label"]
        hostname = record[0]["machine"]["uname_nodename"]

        return {
            "duration": duration,
            "executable": executable,
            "transformation": transformation,
            "hostname": hostname,
            "wf-label": wf_label
        }

    entry["kickstart-record"] = parse_ks_record(entry["kickstart-record"])
    data[out_file.name.split(".")[0]] = entry

def aggregate_transfer_data(data: dict) -> None:
    time_spent_doing_data_movement = 0
    effective_bandwidths = list()
    wan_effective_bandwidths = list()

    for _, job in data.items():
        for t in ["transfer-input", "transfer-output"]:
            if job[t]["duration"] != None:
                value, unit = job[t]["duration"].split(" ")
                assert unit == "seconds"
                time_spent_doing_data_movement += int(value)

            if job[t]["rate"] != None:
                effective_bandwidths.append(job[t]["rate"])

            if t == "transfer-output":
                if job["kickstart-record"]["hostname"] not in {"ccgrid-submit", "ccgrid-worker-1"}\
                        and job[t]["src-dst"] == "condorpool->staging":
                
                    value, unit = job[t]["duration"].split(" ")

                    wan_effective_bandwidths.append(
                                {
                                    "rate": job[t]["rate"],
                                    "duration": int(value)
                                }
                            )


    first_rate = effective_bandwidths[0].split(" ")[1]
    for b in effective_bandwidths:
        value, unit = b.split(" ")
        assert first_rate == unit

    total_wan_xfer_time = sum([d["duration"] for d in wan_effective_bandwidths])
    wan_xfer_sums = 0
    for d in wan_effective_bandwidths:
        value, unit = d["rate"].split(" ")
        duration = d["duration"]
        assert unit == "MB/s"
        wan_xfer_sums += ((duration / total_wan_xfer_time) * float(value))

    data["NOT_A_JOB"] = {
                "wan-effective-bandwidths-in-MBPS": wan_effective_bandwidths,
                "wan-weighted-average-bandwidth-in-MBPS": wan_xfer_sums,
                "cumulative-time-spent-doing-data-movement-in-seconds": time_spent_doing_data_movement
            }

if __name__=="__main__":
    args = parse_args()
    data = dict()

    traverse_submit_dir(args.submit_dir, data)
    aggregate_transfer_data(data)

    with args.output.open("w") as f:
        yaml.dump(data, f)
