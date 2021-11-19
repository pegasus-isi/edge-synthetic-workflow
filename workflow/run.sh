#!/bin/bash
python3 workflow.py \
	--pegasus-keg-path /usr/bin/pegasus-keg \
	--height 2 \
	--runtime 1 2 \
	--output-sizes 10 20 \
	--replica-catalog replicas.yml \
	--job-mapping \
	--submit

watch -n 1 pegasus-status -l $(cat submit_dir_path.txt) 
