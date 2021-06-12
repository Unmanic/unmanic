#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.hardware_acceleration_handle.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     21 Feb 2021, (3:54 PM)

    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved

           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:

           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.

           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
import ctypes
import os


class HardwareAccelerationHandle(object):
    """
    HardwareAccelerationHandle

    Determine support for Hardware Acceleration on host
    """

    def __init__(self, file_probe):
        self.file_probe = file_probe
        self.enable_hardware_accelerated_decoding = False
        self.hardware_device = None
        self.video_encoder = None
        self.main_options = []
        self.advanced_options = []

    def get_hwaccel_devices(self):
        """
        Return a list of the hosts compatible decoders

        :return:
        """
        decoders_list = []

        # Check for CUDA decoders
        decoders_list = decoders_list + self.list_available_cuda_decoders()

        # Append any discovered VAAPI decoders
        decoders_list = decoders_list + self.list_available_vaapi_devices()

        # Return the decoder list
        return decoders_list

    def set_hwaccel_args(self):
        self.main_options = []

        # If Unmanic has settings configured for enabling 'HW Decoding', then fetch args based on selected HW type
        if self.hardware_device:
            hwaccel_type = self.hardware_device.get('hwaccel')
            if hwaccel_type is not None:
                if hwaccel_type == 'vaapi':
                    # Return decoder args for VAAPI
                    self.generate_vaapi_main_args()
                elif hwaccel_type == 'cuda':
                    # Return decoder args for NVIDIA CUDA device
                    self.generate_cuda_main_args()
        else:
            # If no hardware decoder is set, then check that there is no need for setting the hardware device for the encoder
            # Eg. The VAAPI encoder still needs to have the '-vaapi_device' main option configured to work even if no decoder
            #   is configured

            # Check if VAAPI video encoder is enabled
            if self.video_encoder and "vaapi" in self.video_encoder.lower():
                # Find the first decoder
                vaapi_devices = self.list_available_vaapi_devices()
                if vaapi_devices:
                    self.hardware_device = vaapi_devices[0]
                    self.generate_vaapi_main_args()
                    #self.main_options = self.main_options + ['-vaapi_device', vaapi_device.get('hwaccel_device')]

    def update_main_options(self, main_options):
        return main_options + self.main_options

    def update_advanced_options(self, advanced_options):
        return advanced_options + self.advanced_options

    def generate_vaapi_main_args(self):
        """
        Generate a list of args for using a VAAPI decoder

        :return:
        """
        # Check if we are using a VAAPI encoder also...
        if self.video_encoder and "vaapi" in self.video_encoder.lower():
            if self.enable_hardware_accelerated_decoding:
                # Configure args such that when the input may or may not be hardware decodable we can do:
                #   REF: https://trac.ffmpeg.org/wiki/Hardware/VAAPI#Encoding
                self.main_options = [
                    "-init_hw_device", "vaapi=vaapi0:{}".format(self.hardware_device.get('hwaccel_device')),
                    "-hwaccel", "vaapi",
                    "-hwaccel_output_format", "vaapi",
                    "-hwaccel_device", "vaapi0",
                ]
                # Use 'NV12' for hardware surfaces. I would think that 10-bit encoding encoding using
                #   the P010 input surfaces is an advanced feature
                self.advanced_options = [
                    "-filter_hw_device", "vaapi0",
                    "-vf", "format=nv12|vaapi,hwupload",
                ]
            else:
                # Encode only (no decoding)
                #   REF: https://trac.ffmpeg.org/wiki/Hardware/VAAPI#Encode-only (sorta)
                self.main_options = [
                    "-vaapi_device", self.hardware_device.get('hwaccel_device'),
                ]
                # Use 'NV12' for hardware surfaces. I would think that 10-bit encoding encoding using
                #   the P010 input surfaces is an advanced feature
                self.advanced_options = [
                    "-vf", "format=nv12|vaapi,hwupload",
                ]
        else:
            # Decode an input with hardware if possible, output in normal memory to encode with another encoder not vaapi:
            #   REF: https://trac.ffmpeg.org/wiki/Hardware/VAAPI#Decode-only
            self.main_options = [
                "-hwaccel", "vaapi",
                "-hwaccel_device", self.hardware_device.get('hwaccel_device')
            ]

    def generate_cuda_main_args(self):
        """
        Generate a list of args for using an NVIDIA CUDA decoder

        :return:
        """
        self.main_options = ["-hwaccel", "cuda", "-hwaccel_device", self.hardware_device.get('hwaccel_device')]

    def list_available_cuda_decoders(self):
        """
        Check for the existance of a cuda encoder
        Credit for code:
            https://gist.github.com/f0k/63a664160d016a491b2cbea15913d549

        :return:
        """
        decoders = []

        # Search for cuder libs
        libnames = ('libcuda.so', 'libcuda.dylib', 'cuda.dll')
        for libname in libnames:
            try:
                cuda = ctypes.CDLL(libname)
            except OSError:
                continue
            else:
                break
        else:
            return decoders

        # For the available GPUs found, ensure that there is a cuda device
        nGpus = ctypes.c_int()
        device = ctypes.c_int()
        result = cuda.cuInit(0)
        if result != 0:
            return decoders
        result = cuda.cuDeviceGetCount(ctypes.byref(nGpus))
        if result != 0:
            return decoders

        # Loop over GPUs and list each one individually
        for i in range(nGpus.value):
            result = cuda.cuDeviceGet(ctypes.byref(device), i)
            if result != 0:
                continue
            device_data = {
                'hwaccel':        'cuda',
                'hwaccel_device': "{}".format(i),
            }
            decoders.append(device_data)

        return decoders

    def list_available_vaapi_devices(self):
        """
        Return a list of available VAAPI decoder devices

        :return:
        """
        decoders = []
        dir_path = os.path.join("/", "dev", "dri")

        if os.path.exists(dir_path):
            for device in sorted(os.listdir(dir_path)):
                if device.startswith('render'):
                    device_data = {
                        'hwaccel':        'vaapi',
                        'hwaccel_device': os.path.join("/", "dev", "dri", device),
                    }
                    decoders.append(device_data)

        # Return the list of decoders
        return decoders


if __name__ == "__main__":
    hw_a = HardwareAccelerationHandle('blah')
    print(hw_a.get_hwaccel_devices())
    for hardware_decoder in hw_a.get_hwaccel_devices():
        hw_a.hardware_device = hardware_decoder
        break
    print(hw_a.args())
