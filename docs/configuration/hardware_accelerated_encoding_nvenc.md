Unmanic Configuration - NVENC Hardware Acceleration
=====


# Overview

Unmanic supports hardware acceleration (HWA) of video decoding using FFMpeg. FFMpeg and Unmanic can support multiple hardware acceleration implementations such as nVidia NVENC and MediaCodec through Video Acceleration API's.


For more information on NVIDIA using ffmpeg official list, take a look [here](https://developer.nvidia.com/ffmpeg).


It is recommended to use the patched drivers [here](https://github.com/keylase/nvidia-patch) as these will remove the restriction on maximum number of simultaneous NVENC video encoding sessions imposed by Nvidia to consumer-grade GPUs. 

[Here](https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix-new) is the official list of NVIDIA Graphics Cards for supported codecs. 

To ensure you device is capible of running the NVENC encoders, run this command:
```
for i in encoders decoders filters; do     echo $i:; ffmpeg -hide_banner -${i} | egrep -i "npp|cuvid|nvenc|cuda|nvdec"; done
```

You should see a list of available encoders and decoders.

> NOTE:
> The minimum required NVIDIA driver version is 418.30 for this to work in Linux.



# Running Unmanic with support for NVENC

To enable NVENC, you will need to run Unmanic on a device that supports it.

If you intend to use Unmanic inside a Docker container, you will also need to pass through the required devices to the container. Take a look at the [docker-compose-nvidia.yml](/docker/docker-compose-nvidia.yml) Docker-compose template for details on how this is done.



# Enable NVENC in Unmanic Settings

To enable the NVENC FFMpeg encoder, you must select it in the Unmanic's settings. Follow these steps to do this.

  1. Navigate to the **Video Encoding** section of Unmanic's settings.

![Video Encoding](https://raw.githubusercontent.com/Josh5/unmanic/master/docs/images/settings-video-encoding.png)

  2. Select your target **Video Codec**.

  3. Then select the **Video Encoder** that ends with "_nvenc"

  4. Click **SUBMIT**

These changes will only affect any future added files. If you wish to apply this to the current Pending Tasks list, then restart Unmanic.

