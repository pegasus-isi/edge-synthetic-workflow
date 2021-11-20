#!/usr/bin/env python3
import argparse
import pprint
import sys
from pathlib import Path
from typing import List, Dict

import yaml

pp = pprint.PrettyPrinter(indent=4)

def parse_args(args: List[str] = sys.argv[1:]) -> argparse.Namespace:
    pass

def traverse_submit_dir(submit_dir_path: Path, data: Dict) -> None:
    def _traverse(dir: Path, data: Dict) -> None:
        for f in dir.iterdir():
            if not f.is_dir():
                if f.match("*.out.*"):
                    print(f.name)
            else:
                _traverse(f, data)

    _traverse(submit_dir_path, data)


def parse_out_file(out_file: Path, data: Dict) -> None:
    entry = {
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
        pp.pprint(entry)

if __name__=="__main__":
    #traverse_submit_dir(Path("run0005"), dict())
    parse_out_file(
                Path("/Users/ryantanaka/ISI/edge-synthetic-workflow/data-parser/run0005/00/00/keg_merge.out.000"),
                dict()
            )

