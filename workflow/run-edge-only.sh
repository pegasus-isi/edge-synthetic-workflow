#!/bin/bash
set -e

# generate site catalog
python3 generate-sc.py --edge-only

# generate replica catalog
python3 generate-rc.py --compute-on-edge

# run workflow
for i in {1..10}
do
	echo "Doing run ${i}"

	python3 workflow.py \
	    --workflow-name "edge" \
	    --height 3 \
	    --runtime 40 20 60 \
	    --output-sizes 500 250 \
	    --edge-only \
	    --submit
done

# watch till completion
#watch -n 1 pegasus-status -l $(cat submit_dir_path.txt)
