#!/bin/bash

# add MACHINE_SPECIAL_ID attribute which will be used to match jobs
printf "\nMACHINE_SPECIAL_ID = \"$MACHINE_SPECIAL_ID\"\nSTARTD_ATTRS = \$(STARTD_ATTRS) MACHINE_SPECIAL_ID\n" \
    >> /root/config/custom.conf

exec "$@"
