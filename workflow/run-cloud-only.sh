#!/bin/bash
set -e

# generate site catalog
python3 generate-sc.py

# generate replica catalog
python3 generate-rc.py

# run workflow
for i in {1..10}
do
    echo "Doing run ${i}"
    python3 workflow.py \
	--workflow-name "cloud" \
        --height 3 \
	--runtime 40 20 60 \
	--output-sizes 500 250 \
	--cloud-only \
	--submit
done

# watch till completion
#watch -n 1 pegasus-status -l $(cat submit_dir_path.txt)

