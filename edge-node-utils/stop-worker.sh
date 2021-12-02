#!/bin/bash

for i in {1..24}
do
	docker kill --signal SIGINT edge-worker-$i
done
