#!/usr/bin/env python3
import argparse
import pprint
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
                    parse_out_file(f, data)
            else:
                _traverse(f, data)

    _traverse(submit_dir_path, data)


def parse_out_file(out_file: Path, data: Dict) -> None:
    """Parse kickstart *.out.* file in submit directory"""
    entry = {
            "file": out_file.name,
            "kickstart-record": None,
            "pegasus-multipart": list()
        }

    in_multipart = False

    with out_file.open("r") as f:
        ks_record = list()
        multipart_record = list()
        multipart_header = "---------pegasus-multipart"
        for line in f:
            if not in_multipart and multipart_header in line:
                in_multipart = True

            if not in_multipart:
                if multipart_header not in line:
                    ks_record.append(line)
            else:
                if multipart_header not in line:
                    multipart_record.append(line)
                else:
                    if len(multipart_record) != 0:
                        entry["pegasus-multipart"].append(
                                    yaml.load(
                                        "".join(multipart_record),
                                        Loader=yaml.Loader
                                    )
                                )

                        multipart_record = list()

        if len(multipart_record) != 0:
            entry["pegasus-multipart"].append(
                        yaml.load(
                                "".join(multipart_record),
                                Loader=yaml.Loader
                            )
                    )

        entry["kickstart-record"] = yaml.load("".join(ks_record), Loader=yaml.Loader)
        data[out_file.name] = entry

if __name__=="__main__":
    args = parse_args()
    data = dict()

    traverse_submit_dir(args.submit_dir, data)

    with args.output.open("w") as f:
        yaml.dump(data, f)


