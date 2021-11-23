#!/bin/bash
set -e

python3 generate-edge-cloud-site-catalog.py

python3 generate-rc.py

python3 workflow.py \
	--pegasus-keg-path /usr/bin/pegasus-keg \
	--height 2 \
	--runtime 20 20 \
	--output-sizes 1024 2048 \
	--replica-catalog replicas.yml \
	--job-mapping \
	--submit

watch -n 1 pegasus-status -l $(cat submit_dir_path.txt) 
