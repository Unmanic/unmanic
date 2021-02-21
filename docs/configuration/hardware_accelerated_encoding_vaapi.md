Unmanic Configuration - VAAPI Hardware Acceleration
=====


# Overview

Unmanic supports hardware acceleration (HWA) of video decoding using FFMpeg. FFMpeg and Unmanic can support multiple hardware acceleration implementations such as nVidia NVENC and MediaCodec through Video Acceleration API's.


VAAPI is a Video Acceleration API that uses libva to interface with local drivers to provide HWA.


You can find a list of supported codecs for VAAPI [here](https://wiki.archlinux.org/index.php/Hardware_video_acceleration#Comparison_tables).
Both Intel iGPU and AMD GPU can use VAAPI.

> NOTE:
> AMD GPU requires open source driver Mesa 20.1 or higher to support hardware decoding HEVC.



# Running Unmanic with support for VAAPI

To enable VAAPI, you will need to run Unmanic on a device that supports it.

If you intend to use Unmanic inside a Docker container, you will also need to pass through the required devices to the container. Take a look at the [docker-compose-vaapi.yml](/docker/docker-compose-vaapi.yml) Docker-compose template for details on how this is done.



# Enable VAAPI in Unmanic Settings

To enable the VAAPI FFMpeg encoder, you must select it in the Unmanic's settings. Follow these steps to do this.

  1. Navigate to the **Video Encoding** section of Unmanic's settings.

![Video Encoding](https://raw.githubusercontent.com/Josh5/unmanic/master/docs/images/settings-video-encoding.png)

  2. Select your target **Video Codec**.

  3. Then select the **Video Encoder** that ends with "_vaapi"

  4. Click **SUBMIT**

  5. Now switch to the **Advanced Options** section of Unmanic's settings.

![Advanced Options](https://raw.githubusercontent.com/Josh5/unmanic/master/docs/images/settings-advanced-options.png)

  6. Add the following lines:

```
-vf format=nv12|vaapi,hwupload 
```
> NOTE: For more details on filtering for VAAPI encoders, see the [FFMPEG VAAPI Docs](https://trac.ffmpeg.org/wiki/Hardware/VAAPI) 
> and the [FFMPEG Filtering Guide Docs](https://trac.ffmpeg.org/wiki/FilteringGuide).

  7. Click **SUBMIT**

These changes will only affect any future added files. If you wish to apply this to the current Pending Tasks list, then restart Unmanic.

