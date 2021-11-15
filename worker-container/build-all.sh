#!/bin/bash
set -e

POOL_PASSWORD=kevinMalone

for d in central-manager execute submit
do
    cd ./$d
    echo building $d
    docker image build --build-arg POOL_PASSWORD=$POOL_PASSWORD -t $USER/$d .
    cd ../
done


