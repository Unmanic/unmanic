#! /bin/bash

SCRIPT_PATH=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd );
OUT_DIR=$(realpath ${SCRIPT_PATH}/../tests/tmp/ffmpeg_tests);
IN_FILE=$(realpath ${SCRIPT_PATH}/../tests/support_/videos/med/big_buck_bunny_720p_10mb.mp4);

# Set the container
CONTAINER_EXT="mkv"
# Select video encoder:
#   - libx265
#   - nvenc_hevc (depreciated)
#   - hevc_nvenc
#   - h264_nvenc
V_ENCODER="hevc_nvenc"
# Additional encoder args
#   EG:
#       -b:v 5M
#       -b:v 1M -maxrate 2M -bufsize 4M -preset slow
V_ENCODER_ARGS=""



if [[ ! -z ${1} && "${1}" == "probe" ]]; then
    # Prove file first
    CMD="ffprobe \
        -loglevel quiet \
        -print_format json \
        -show_format \
        -show_streams \
        -show_error\
        ${IN_FILE}"

    echo "${CMD}"
    bash -c "${CMD}"
    exit 0
elif [[ ! -z ${1} && "${1}" == "encoders" ]]; then
    # List encoders
    CMD="ffmpeg \
        -loglevel quiet \
        -encoders"

    echo "${CMD}"
    bash -c "${CMD}"
    exit 0
else
    mkdir -p ${OUT_DIR}
    CMD="ffmpeg \
        -i ${IN_FILE} \
        -map 0:0 \
        -map 0:1 \
        -c:v ${V_ENCODER} \
        ${V_ENCODER_ARGS} \
        -c:a copy \
        -y ${OUT_DIR}/outfile.${CONTAINER_EXT}"

    start_time=`date +%s`
    echo "${CMD}"
    bash -c "${CMD}"
    end_time=`date +%s`

    echo
    echo
    echo "Task took $((end_time-start_time)) seconds"
    echo
    echo "Input file:"
    du -h ${IN_FILE}
    echo
    echo "Output file:"
    du -h ${OUT_DIR}/*.${CONTAINER_EXT}
    echo
    exit 0
fi
