#!/usr/bin/env bash

filename="makespans.pdf"
echo $filename
gnuplot<<EOC
    reset
    set terminal pdf size 16,10 font 'Calibri Bold, 40'
    set output "$filename"
    set datafile separator ","
    set style fill solid 0.5 border -1
    set style histogram errorbars gap 1 lw 1
    set style data histogram
    set boxwidth 0.9

    #set title 'Stitchport 1Gbps Single Workflow Makespan' noenhanced
    set notitle
    set yrange [0:1200]
    set ylabel 'Makespan (Seconds)'
    set xlabel 'Workflow'

    set key outside top right horizontal

    plot 'edge-makespans.dat' using 3:2:4:xtic(1) title 'Edge',\
    'edge-cloud-makespans.dat' using 3:2:4:xtic(1) title 'Edge-Cloud',\
    'cloud-makespans.dat' using 3:2:4:xtic(1) title 'Cloud'
EOC

filename="cumulative-job-walltime.pdf"
echo $filename
gnuplot<<EOC
    reset
    set terminal pdf size 16,10 font 'Calibri Bold, 40'
    set output "$filename"
    set datafile separator ","
    set style fill solid 0.5 border -1
    set style histogram errorbars gap 1 lw 1
    set style data histogram
    set boxwidth 0.9

    #set title 'Stitchport 1Gbps Single Workflow Makespan' noenhanced
    set notitle
    set ylabel 'Cumulative Job Walltime (Seconds)'
    set xlabel 'Workflow'
    
    set key outside top right horizontal

    plot 'edge-cumulative-job-walltime.dat' using 3:2:4:xtic(1) title 'Edge',\
    'edge-cloud-cumulative-job-walltime.dat' using 3:2:4:xtic(1) title 'Edge-Cloud',\
    'cloud-cumulative-job-walltime.dat' using 3:2:4:xtic(1) title 'Cloud'
EOC

filename="cumulative-job-walltime-submit.pdf"
echo $filename
gnuplot<<EOC
    reset
    set terminal pdf size 16,10 font 'Calibri Bold, 40'
    set output "$filename"
    set datafile separator ","
    set style fill solid 0.5 border -1
    set style histogram errorbars gap 1 lw 1
    set style data histogram
    set boxwidth 0.9
    
    set key outside top right horizontal

    #set title 'Stitchport 1Gbps Single Workflow Makespan' noenhanced
    set notitle
    set ylabel 'Cumulative Job Walltime (Seconds)'
    set xlabel 'Workflow'

    plot 'edge-cumulative-job-walltime-submit.dat' using 3:2:4:xtic(1) title 'Edge',\
    'edge-cloud-cumulative-job-walltime-submit.dat' using 3:2:4:xtic(1) title 'Edge-Cloud',\
    'cloud-cumulative-job-walltime-submit.dat' using 3:2:4:xtic(1) title 'Cloud'
EOC

filename="cumulative-transfer-time.pdf"
echo $filename
gnuplot<<EOC
    reset
    set terminal pdf size 16,10 font 'Calibri Bold, 40'
    set output "$filename"
    set datafile separator ","
    set style fill solid 0.5 border -1
    set style histogram errorbars gap 1 lw 1
    set style data histogram
    set boxwidth 0.9

    set key outside top right horizontal

    #set title 'Stitchport 1Gbps Single Workflow Makespan' noenhanced
    set notitle
    set ylabel 'Cumulative Transfer Time (Seconds)'
    set xlabel 'Workflow'

    plot 'edge-cumulative-transfers.dat' using 3:2:4:xtic(1) title 'Edge',\
    'edge-cloud-cumulative-transfers.dat' using 3:2:4:xtic(1) title 'Edge-Cloud',\
    'cloud-cumulative-transfers.dat' using 3:2:4:xtic(1) title 'Cloud'
EOC

filename="wan-data-transfers.pdf"
echo $filename
gnuplot<<EOC
    reset
    set terminal pdf size 16,10 font 'Calibri Bold, 40'
    set output "$filename"
    set datafile separator ","
    set style fill solid 0.5 border -1
    set style histogram gap 1
    set style data histogram
    set boxwidth 0.9

    set key outside top right horizontal

    #set title 'Stitchport 1Gbps Single Workflow Makespan' noenhanced
    set notitle
    set logscale y 2
    set yrange [:65536]

    set ylabel 'Data (MB)'
    set xlabel 'Workflow'

    plot 'wan-data-transfers.dat' using 2:xtic(1) title 'Edge',\
    '' using 3:xtic(1) title 'Edge-Cloud',\
    '' using 4:xtic(1) title 'Cloud'
EOC
