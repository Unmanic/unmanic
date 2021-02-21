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
        self.hardware_decoder = None
        self.video_encoder = None
        self.acceleration_args = []

    def get_decoders(self):
        """
        Return a list of the hosts compatible decoders

        :return:
        """
        decoders_list = []

        # Check for CUDA decoders
        decoders_list = decoders_list + self.list_available_cuda_decoders()

        # Append any discovered VAAPI decoders
        decoders_list = decoders_list + self.list_available_vaapi_decoders()

        # Return the decoder list
        return decoders_list

    def args(self):
        self.acceleration_args = []
        if self.hardware_decoder:
            hwaccel = self.hardware_decoder.get('hwaccel')
            hwaccel_device = self.hardware_decoder.get('hwaccel_device')
            if hwaccel is not None and hwaccel_device is not None:
                if hwaccel == 'vaapi':
                    # Return decoder args for VAAPI
                    self.acceleration_args = self.generate_vaapi_args()
                elif hwaccel == 'cuda':
                    # Return decoder args for NVIDIA CUDA device
                    self.acceleration_args = self.generate_cuda_args()
        else:
            # If no hardware decoder is set, then check that there is no need for setting the hardware device for the encoder
            if self.video_encoder and "vaapi" in self.video_encoder.lower():
                vaapi_decoders = self.list_available_vaapi_decoders()
                if vaapi_decoders:
                    vaapi_decoder = vaapi_decoders[0]
                    self.acceleration_args = self.acceleration_args + ['-vaapi_device', vaapi_decoder.get('hwaccel_device')]

        return self.acceleration_args

    def generate_vaapi_args(self):
        """
        Generate a list of args for using a VAAPI decoder

        :return:
        """
        args = ["-hwaccel", "vaapi", "-hwaccel_device", self.hardware_decoder.get('hwaccel_device')]

        if self.video_encoder and "vaapi" in self.video_encoder.lower():
            # If the decoder and encoder are both the same vaapi device, then we need an additional argument
            args = args + ["-hwaccel_output_format", "vaapi"]

        return args

    def generate_cuda_args(self):
        """
        Generate a list of args for using an NVIDIA CUDA decoder

        :return:
        """
        args = ["-hwaccel", "cuda", "-hwaccel_device", self.hardware_decoder.get('hwaccel_device')]

        return args

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

    def list_available_vaapi_decoders(self):
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
    print(hw_a.get_decoders())
    for hardware_decoder in hw_a.get_decoders():
        hw_a.hardware_decoder = hardware_decoder
        break
    print(hw_a.args())
