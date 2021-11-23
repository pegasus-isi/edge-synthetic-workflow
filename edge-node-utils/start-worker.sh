#!/bin/bash
docker container run \
    --cpus=1 \
    -e MACHINE_SPECIAL_ID=1 \
    -e CONDOR_HOST=10.100.101.107 \
    -e NUM_CPUS=1 \
    --rm \
    --detach \
    --name edge-worker-$1 \
    -v /home/panorama/public_html:/home/panorama/public_html \
    ryantanaka/execute