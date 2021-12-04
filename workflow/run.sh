#!/bin/bash
set -e
./run-edge-cloud.sh
./run-edge-only.sh
./run-cloud-only.sh
