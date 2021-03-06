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

TEMP_FRONT="/tmp/temp_front.mp4"
TEMP_REAR="/tmp/temp_rear.mp4"
FRONT_OUTPUT=$(basename "${FILENAME%.*}")_FRONT.mp4
REAR_OUTPUT=$(basename "${FILENAME%.*}")_REAR.mp4

LOGLEVEL="-loglevel warning"

WIDTH=1920
HEIGHT_FRONT=1080
HEIGHT_REAR=1000
SCALE=4
SCALE_X=$((${WIDTH}/${SCALE}))
SCALE_Y_FRONT=$((${HEIGHT_FRONT}/${SCALE}))
SCALE_Y_REAR=$((${HEIGHT_REAR}/${SCALE}))

echo "---------------------------------------------"
echo "Input file: ${FILENAME}"
echo "Front Output File: ${FRONT_OUTPUT}"
echo "Rear Output File: ${REAR_OUTPUT}"
echo "Video"
echo "  Width: ${WIDTH}"
echo "  Front Height: ${HEIGHT_FRONT}"
echo "  Rear Height: ${HEIGHT_REAR}"
echo " Scale ${SCALE}"
echo "  Width: ${SCALE_X}"
echo "  Front Height: ${SCALE_Y_FRONT}"
echo "  Rear Height: ${SCALE_Y_REAR}"
echo "---------------------------------------------"


echo "---------------------------------------------"
echo "Create Temporary files for both cameras"
echo "---------------------------------------------"
ffmpeg ${LOGLEVEL} -y -i "${FILENAME}" -map 0:0 ${TEMP_FRONT} \
-filter:v "crop=1920:1000:0:0, hflip" -map 0:1 ${TEMP_REAR} 

echo "---------------------------------------------"
echo "Create Front View as Primary"
echo "---------------------------------------------"
ffmpeg ${LOGLEVEL} -y -i ${TEMP_FRONT} -i ${TEMP_REAR} \
-filter_complex "[1:v] scale=${SCALE_X}:${SCALE_Y_REAR} [1v]; [0:v][1v] overlay=x=1440:y=0 [outv]" \
-map "[outv]" ${FRONT_OUTPUT}

echo "---------------------------------------------"
echo "Create Rear View as Primary"
echo "---------------------------------------------"
ffmpeg ${LOGLEVEL} -y -i ${TEMP_REAR} -i ${TEMP_FRONT} \
-filter_complex "[1:v] scale=${SCALE_X}:${SCALE_Y_FRONT} [1v]; [0:v][1v] overlay=x=1440:y=0 [outv]" \
-map "[outv]" ${REAR_OUTPUT}


rm -f ${TEMP_FRONT}
rm -f ${TEMP_REAR}

