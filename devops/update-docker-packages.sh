#!/usr/bin/env bash

runtime_packages=(
    "libexpat1"
    "libgl1-mesa-dri"
    "libglib2.0-0"
    "libgomp1"
    "libharfbuzz0b"
    "libmediainfo0v5"
    "libv4l-0"
    "libx11-6"
    "libxcb1"
    "libxext6"
    "libxml2"
)
intel_media_driver_packages=(
    "i965-va-driver"
    "intel-igc-cm"
    "intel-level-zero-gpu"
    "intel-media-va-driver-non-free"
    "intel-opencl-icd"
    "level-zero"
    "libigc1"
    "libigdfcl1"
    "libigdgmm11"
    "libmfx1"
    "libva-drm2"
    "libva-wayland2"
    "libva-x11-2"
    "libva2"
    "vainfo"
)

apt-get update
apt list --upgradable 2> /dev/null 1> /tmp/apt-updates.txt

echo
echo "Runtime package updates"
echo
for package in ${runtime_packages[@]}; do
    update_version=$(cat /tmp/apt-updates.txt | grep "${package}/" | awk '{print $2}');
    if [[ -z ${update_version} ]]; then
        if [[ ${1:-X} == 'all' ]]; then
            current_version=$(dpkg -s "${package}" | grep Version | awk '{print $2}')
            echo "            ${package}=${current_version} \\"
        fi
        continue
    fi
    echo "            ${package}=${update_version} \\"
done
echo

echo
echo "Intel media driver package updates"
echo
for package in ${intel_media_driver_packages[@]}; do
    update_version=$(cat /tmp/apt-updates.txt | grep "${package}/" | awk '{print $2}');
    if [[ -z ${update_version} ]]; then
        if [[ ${1:-X} == 'all' ]]; then
            current_version=$(dpkg -s "${package}" | grep Version | awk '{print $2}')
            echo "                    ${package}=${current_version} \\"
        fi
        continue
    fi
    echo "                    ${package}=${update_version} \\"
done
echo
