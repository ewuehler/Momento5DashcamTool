#!/bin/bash

FILENAME=""
if [ "$1" != "" ]; then
    FILENAME=$1
else
    echo "Missing Filename!"
    echo ""
    echo "Usage:"
    echo "  $0 <filename>"
    echo ""
    exit
fi

FRONT="/tmp/temp_front.mp4"
REAR="/tmp/temp_rear.mp4"
OUTPUT=$(basename ${FILENAME%.*}).mp4

echo "Input file: $(basename ${FILENAME})"
echo "Output File: $(basename ${OUTPUT})"


ffmpeg -i ${FILENAME} -map 0:0 ${FRONT} \
-filter:v "crop=1920:900:0:0" -map 0:1 ${REAR} 

ffmpeg -y -i ${FRONT} -i ${REAR} \
-filter_complex "[1:v] scale=480:225 [1v]; [0:v][1v] overlay=x=1440:y=0 [outv]" \
-map "[outv]" ${OUTPUT}

rm -f ${FRONT}
rm -f ${REAR}

