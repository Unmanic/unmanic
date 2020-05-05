#! /bin/bash

SCRIPT_PATH=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd );
IN_FILE=$(realpath ${SCRIPT_PATH}/../tests/support_/videos/med/big_buck_bunny_720p_10mb.mp4);
OUT_DIR=$(realpath ${SCRIPT_PATH}/../tests/tmp/ffmpeg_tests);


# Select video encoder:
#   - libx265
#   - nvenc_hevc (depreciated)
#   - hevc_nvenc
#   - hevc_vaapi
V_ENCODER="nvenc_hevc"



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
    CMD="ffmpeg -i ${IN_FILE} \
        -map 0:0 \
        -map 0:1 \
        -c:v ${V_ENCODER} \
        -c:a:1 libmp3lame -b:a:0 192k -ac 2 \
        -y ${OUT_DIR}/outfile.mkv"

    echo "${CMD}"
    bash -c "${CMD}"

    ls -l ${OUT_DIR}/
    exit 0
fi
