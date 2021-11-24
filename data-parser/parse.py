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
                "rate": tokens[14] + " " + tokens[15]
            }

    if "register_staging" not in out_file.name and\
            "cleanup_" not in out_file.name and\
            "clean_up_" not in out_file.name and\
            "create_dir" not in out_file.name and\
            "stage_out" not in out_file.name:
        err_file = Path(out_file.name.replace(".out.", ".err.")) 
        err_file = out_file.resolve().parent / err_file

        transfer_input = list()
        transfer_input_metrics = None

        transfer_output = list()
        transfer_output_metrics = None

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

                        transfer_input.append(l)

                if "Staging out output files" in l:
                    while "PegasusLite: " not in l:
                        l = f.readline()

                        if "Stats: Total" in l:
                            transfer_output_metrics = get_xfer_stats(l)

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

    data[out_file.name.split(".")[0]] = entry


if __name__=="__main__":
    args = parse_args()
    data = dict()

    traverse_submit_dir(args.submit_dir, data)

    with args.output.open("w") as f:
        yaml.dump(data, f)
