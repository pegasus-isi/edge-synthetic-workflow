#!/bin/bash

interface="eno1"
bandwidth="1000"

tc qdisc add dev $interface root handle 1: htb default 11
tc class add dev $interface parent 1: classid 1:1 htb rate ${bandwidth}mbit
tc class add dev $interface parent 1:1 classid 1:11 htb rate ${bandwidth}mbit
tc qdisc add dev $interface parent 1:11 handle 20: sfq perturb 10
timestamp=$(date '+%d/%m/%Y %H:%M:%S');
echo "[$timestamp] Upload bandwidth limited to $bandwidth Mbits (IF: $interface)"

#tc qdisc del dev $interface root