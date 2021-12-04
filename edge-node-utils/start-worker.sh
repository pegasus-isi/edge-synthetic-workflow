#!/bin/bash

for i in {1..24}
do
        docker container run \
            --cpus="0.67" \
            -e MACHINE_SPECIAL_ID=1 \
            -e CONDOR_HOST=10.100.101.107 \
            -e NUM_CPUS=1 \
            --rm \
            --detach \
            --name edge-worker-$i \
            -v /home/panorama/public_html:/home/panorama/public_html \
            ryantanaka/execute
done
