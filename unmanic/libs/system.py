#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.system.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Mar 2021, (11:00 PM)

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
from unmanic.libs import unlogger, common
from unmanic.libs.singleton import SingletonType


class System(object, metaclass=SingletonType):
    devices = {}
    ffmpeg = {}
    platform = {}
    python_version = {}

    def __init__(self, *args, **kwargs):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def __get_python_info(self):
        """
        Return a string of the python version

        :return:
        """
        import sys
        if not self.python_version:
            self.python_version = "{0}.{1}.{2}.{3}.{4}".format(*sys.version_info)
        return self.python_version

    def __get_devices_info(self):
        """
        Return a dictionary of device information

        :return:
        """
        import cpuinfo
        import gpuinfo.nvidia as nvidia_info
        gpu_devices = []
        try:
            for gpu in nvidia_info.get_gpus():
                gpu_info = gpu.__dict__
                gpu_info['get_max_clock_speeds'] = gpu.get_max_clock_speeds()
                gpu_info['get_clock_speeds'] = gpu.get_clock_speeds()
                gpu_info['get_memory_details'] = gpu.get_memory_details()
                gpu_devices.append(gpu_info)
        except FileNotFoundError as e:
            self._log("NVIDIA GPU support not available")
        if not self.devices:
            self.devices = {
                "cpu_info": cpuinfo.get_cpu_info(),
                "gpu_info": gpu_devices,
            }
        return self.devices

    def __get_ffmpeg_info(self):
        """
        Return a dictionary of ffmpeg information

        TODO:
            Parse codecs

        :return:
        """
        from unmanic.libs import unffmpeg
        ffmpeg_info = unffmpeg.Info()
        if not self.ffmpeg:
            self.ffmpeg = {
                "versions":                ffmpeg_info.versions(),
                "hw_acceleration_methods": ffmpeg_info.get_available_ffmpeg_hw_acceleration_methods(),
                "decoders":                ffmpeg_info.get_available_ffmpeg_decoders(),
                "encoders":                ffmpeg_info.get_available_ffmpeg_encoders(),
            }
        return self.ffmpeg

    def __get_platform_info(self):
        """
        Return a dictionary of device information

        :return:
        """
        import platform
        if not self.platform:
            self.platform = platform.uname()
        return self.platform

    def info(self):
        """
        Returns a dictionary of system information

        :return:
        """
        info = {
            "devices":  self.__get_devices_info(),
            "ffmpeg":   self.__get_ffmpeg_info(),
            "platform": self.__get_platform_info(),
            "python":   self.__get_python_info(),
        }
        return info


if __name__ == "__main__":
    import json, sys, os

    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(project_dir)
    sys.path.append(project_dir)
    system = System()
    print(json.dumps(system.info(), indent=2))
