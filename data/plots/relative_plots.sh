#!/usr/bin/env bash

awk -F',' '{str1=$1; str2=$3; getline < "edge-cloud-makespans.dat"; str3=$3; getline < "cloud-makespans.dat"; print str1","str2","str3","$3 > "tmp_makespans.dat"}' edge-makespans.dat
filename="relative-makespans.pdf"
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

    #set title 'Stitchport 1Gbps Single Workflow Makespan' noenhanced
    set notitle
    set yrange [0:]
    set ylabel 'Relative Makespan (%)'
    set xlabel 'Workflow'

    set key outside top right horizontal
    
    round(x) = x - floor(x) < 0.5 ? floor(x) : ceil(x)
    my_pos(a, b) = (a + b)
    my_val_1(a, b) = ((a)/(b)*100)
    my_val_2(a, b) = ((a)/(b)*100 + 5)
    my_label(a, b) = sprintf("%.0f\%", round(my_val_1(a,b)))
    
    plot 'tmp_makespans.dat' using (my_val_1(\$2,\$2)):xtic(1) title 'Edge',\
    '' using (my_pos(\$0,-1./4)):(my_val_2(\$2,\$2)):(my_label(\$2,\$2)) with labels font ",24" notitle,\
    '' using (my_val_1(\$3,\$2)):xtic(1) title 'Edge-Cloud',\
    '' using 0:(my_val_2(\$3,\$2)):(my_label(\$3,\$2)) with labels font ",24" notitle,\
    '' using (my_val_1(\$4,\$2)):xtic(1) title 'Cloud',\
    '' using (my_pos(\$0,1./4)):(my_val_2(\$4,\$2)):(my_label(\$4,\$2)) with labels font ",24" notitle
EOC
rm tmp_makespans.dat

awk -F',' '{str1=$1; str2=$3; getline < "edge-cloud-cumulative-job-walltime.dat"; str3=$3; getline < "cloud-cumulative-job-walltime.dat"; print str1","str2","str3","$3 > "tmp_cumulative_job_walltime.dat"}' edge-cumulative-job-walltime.dat
filename="relative-cumulative-job-walltime.pdf"
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

    #set title 'Stitchport 1Gbps Single Workflow Makespan' noenhanced
    set notitle
    set yrange [0:120]
    set ylabel 'Relative Cumulative Job Walltime (%)'
    set xlabel 'Workflow'
    
    set key outside top right horizontal

    round(x) = x - floor(x) < 0.5 ? floor(x) : ceil(x)
    my_pos(a, b) = (a + b)
    my_val_1(a, b) = ((a)/(b)*100)
    my_val_2(a, b) = ((a)/(b)*100 + 5)
    my_label(a, b) = sprintf("%.0f\%", round(my_val_1(a,b)))
    
    plot 'tmp_cumulative_job_walltime.dat' using (my_val_1(\$2,\$2)):xtic(1) title 'Edge',\
    '' using (my_pos(\$0,-1./4)):(my_val_2(\$2,\$2)):(my_label(\$2,\$2)) with labels font ",24" notitle,\
    '' using (my_val_1(\$3,\$2)):xtic(1) title 'Edge-Cloud',\
    '' using 0:(my_val_2(\$3,\$2)):(my_label(\$3,\$2)) with labels font ",24" notitle,\
    '' using (my_val_1(\$4,\$2)):xtic(1) title 'Cloud',\
    '' using (my_pos(\$0,1./4)):(my_val_2(\$4,\$2)):(my_label(\$4,\$2)) with labels font ",24" notitle
EOC
rm tmp_cumulative_job_walltime.dat

awk -F',' '{str1=$1; str2=$3; getline < "edge-cloud-cumulative-job-walltime-submit.dat"; str3=$3; getline < "cloud-cumulative-job-walltime-submit.dat"; print str1","str2","str3","$3 > "tmp_cumulative_job_walltime_submit.dat"}' edge-cumulative-job-walltime-submit.dat
filename="relative-cumulative-job-walltime-submit.pdf"
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
    set yrange [0:]
    set ylabel 'Relative Cumulative Job Walltime (%)'
    set xlabel 'Workflow'

    round(x) = x - floor(x) < 0.5 ? floor(x) : ceil(x)
    my_pos(a, b) = (a + b)
    my_val_1(a, b) = ((a)/(b)*100)
    my_val_2(a, b) = ((a)/(b)*100 + 10)
    my_label(a, b) = sprintf("%.0f\%", round(my_val_1(a,b)))
    
    plot 'tmp_cumulative_job_walltime_submit.dat' using (my_val_1(\$2,\$2)):xtic(1) title 'Edge',\
    '' using (my_pos(\$0,-1./4)):(my_val_2(\$2,\$2)):(my_label(\$2,\$2)) with labels font ",24" notitle,\
    '' using (my_val_1(\$3,\$2)):xtic(1) title 'Edge-Cloud',\
    '' using 0:(my_val_2(\$3,\$2)):(my_label(\$3,\$2)) with labels font ",24" notitle,\
    '' using (my_val_1(\$4,\$2)):xtic(1) title 'Cloud',\
    '' using (my_pos(\$0,1./4)):(my_val_2(\$4,\$2)):(my_label(\$4,\$2)) with labels font ",24" notitle
EOC
rm tmp_cumulative_job_walltime_submit.dat

awk -F',' '{str1=$1; str2=$3; getline < "edge-cloud-cumulative-transfers.dat"; str3=$3; getline < "cloud-cumulative-transfers.dat"; print str1","str2","str3","$3 > "tmp_cumulative_transfers.dat"}' edge-cumulative-transfers.dat
filename="relative-cumulative-transfer-time.pdf"
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
    set yrange [0:]
    
    set ylabel 'Relative Cumulative Transfer Time (%)'
    set xlabel 'Workflow'

    round(x) = x - floor(x) < 0.5 ? floor(x) : ceil(x)
    my_pos(a, b) = (a + b)
    my_val_1(a, b) = ((a)/(b)*100)
    my_val_2(a, b) = ((a)/(b)*100 + 100)
    my_label(a, b) = sprintf("%.0f\%", round(my_val_1(a,b)))
    
    plot 'tmp_cumulative_transfers.dat' using (my_val_1(\$2,\$2)):xtic(1) title 'Edge',\
    '' using (my_pos(\$0,-1./4)):(my_val_2(\$2,\$2)):(my_label(\$2,\$2)) with labels font ",24" notitle,\
    '' using (my_val_1(\$3,\$2)):xtic(1) title 'Edge-Cloud',\
    '' using 0:(my_val_2(\$3,\$2)):(my_label(\$3,\$2)) with labels font ",24" notitle,\
    '' using (my_val_1(\$4,\$2)):xtic(1) title 'Cloud',\
    '' using (my_pos(\$0,1./4)):(my_val_2(\$4,\$2)):(my_label(\$4,\$2)) with labels font ",24" notitle
EOC
rm tmp_cumulative_transfers.dat

filename="relative-wan-data-transfers.pdf"
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
    #set yrange [0:]
    
    set logscale y 10

    set ylabel 'Relative Data (%)'
    set xlabel 'Workflow'

    round(x) = x - floor(x) < 0.5 ? floor(x) : ceil(x)
    my_pos(a, b) = (a + b)
    my_val_1(a, b) = ((a)/(b)*100)
    my_val_2(a, b) = ((a)/(b)*100 + 5)
    my_label(a, b) = sprintf("%.0f\%", round(my_val_1(a,b)))
    
    plot 'wan-data-transfers.dat' using (my_val_1(\$2,\$2)):xtic(1) title 'Edge',\
    '' using (my_val_1(\$3,\$2)):xtic(1) title 'Edge-Cloud',\
    '' using (my_val_1(\$4,\$2)):xtic(1) title 'Cloud'
    #'' using (my_pos(\$0,-1./4)):(my_val_2(\$2,\$2)):(my_label(\$2,\$2)) with labels font ",24" notitle,\
    #'' using 0:(my_val_2(\$3,\$2)):(my_label(\$3,\$2)) with labels font ",24" notitle,\
    #'' using (my_pos(\$0,1./4)):(my_val_2(\$4,\$2)):(my_label(\$4,\$2)) with labels font ",24" notitle
EOC
