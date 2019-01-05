#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################################################################
#
#   Written by:               Josh.5 <jsunnex@gmail.com>
#   Date:                     Thu Jan 03 2019, (11:23:45 AM)
#
#   Copyright:
#          Copyright (C) Josh Sunnex - All Rights Reserved
#
#          Permission is hereby granted, free of charge, to any person obtaining a copy
#          of this software and associated documentation files (the "Software"), to deal
#          in the Software without restriction, including without limitation the rights
#          to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#          copies of the Software, and to permit persons to whom the Software is
#          furnished to do so, subject to the following conditions:
# 
#          The above copyright notice and this permission notice shall be included in all
#          copies or substantial portions of the Software.
# 
#          THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#          EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#          MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#          IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#          DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#          OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#          OR OTHER DEALINGS IN THE SOFTWARE.
#
#
###################################################################################################


import os
import subprocess
import json
import shutil
import re
import pexpect

from lib import common



class FFMPEGHandle(object):
    def __init__(self, settings, messages):
        self.name       = 'FFMPEGHandle'
        self.settings   = settings
        self.messages   = messages

        # These variables are from the currently processed file (during a encoding task)
        self.duration   = None
        self.src_fps    = None
        self.time       = None
        self.percent    = 0
        self.frame      = None
        self.fps        = None
        self.speed      = None
        self.bitrate    = None
        self.file_size  = None

    def _log(self, message, message2 = '', level = "info"):
        message = "[{}] {}".format(self.name, message)
        self.messages.put({
              "message":message
            , "message2":message2
            , "level":level
        })

    def fileProbe(self, vid_file_path):
        ''' Give a json from ffprobe command line

        @vid_file_path : The absolute (full) path of the video file, string.
        '''
        if type(vid_file_path) != str:
            raise Exception('Give ffprobe a full file path of the video')
            return

        command = ["ffprobe",
                "-loglevel",  "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                vid_file_path
            ]

        try:
            pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out, err = pipe.communicate()
            return json.loads(out.decode("utf-8"))
        except Exception as e: 
            self._log("Exception - file_probe: {}".format(e))
            return False


    def getCurrentVideoCodecs(self, file_properties):
        codecs = []
        for stream in file_properties['streams']:
            if stream['codec_type'] == 'video':
                codecs.append(stream['codec_name'])
        return codecs


    def checkFileToBeProcessed(self, vid_file_path):
        # TODO: Add variable to force conversion based on audio config also
        file_properties = self.fileProbe(vid_file_path)
        if not file_properties:
            # Failed to fetch properties
            if self.settings.DEBUGGING:
                self._log("Failed to fetch properties of file {}".format(vid_file_path))
                self._log("Marking file not to be processed")
            return False
        for stream in file_properties['streams']:
            if stream['codec_type'] == 'video':
                # Check if this file is already the right format
                if stream['codec_name'] == self.settings.VIDEO_CODEC:
                    if self.settings.DEBUGGING:
                        self._log("File already {} - {}".format(self.settings.VIDEO_CODEC,vid_file_path))
                    return False
        return True


    def testFilePostProcess(self, vid_file_path):
        file_properties = self.fileProbe(vid_file_path)
        if not file_properties:
            # Failed to fetch properties
            return False
        result = False
        for stream in file_properties['streams']:
            if stream['codec_type'] == 'video':
                # Check if this file is the right codec
                if stream['codec_name'] == self.settings.VIDEO_CODEC:
                    result = True
                elif self.settings.DEBUGGING:
                    self._log("File is the not correct codec {} - {}".format(self.settings.VIDEO_CODEC,vid_file_path))
                #TODO: Test duration is the same as src
        return result

    def processFile(self, vid_file_path):
        # Parse input path
        srcFile     = os.path.basename(vid_file_path)
        srcPath     = os.path.abspath(vid_file_path)
        srcFolder   = os.path.dirname(srcPath)

        # Parse an output cache path
        outFile     = "{}.{}".format(os.path.splitext(srcFile)[0], self.settings.OUT_CONTAINER)
        outPath     = os.path.join(self.settings.CACHE_PATH,outFile)
        # Create output path if not exists 
        common.ensureDir(outPath)
        # Convert file
        success     = False
        ffmpeg_args = self.generateFFMPEGArgs(srcPath,outPath)
        success = self.execConvertFile(ffmpeg_args)
        if success:
            # Move file back to original folder and remove source
            success = self.testFilePostProcess(outPath)
            if success:
                destPath    = os.path.join(srcFolder,outFile)
                self._log("Moving file {} --> {}".format(outPath,destPath))
                shutil.move(outPath, destPath)
                success     = self.testFilePostProcess(destPath)
                if success:
                    # If successful move, remove source
                    #TODO: Add env variable option to keep src
                    if srcPath != destPath:
                        self._log("Removing source: {}".format(srcPath))
                        os.remove(srcPath)
                else:
                    self._log("Copy / Replace failed during post processing '{}'".format(outPath))
                    return False
            else:
                self._log("Encoded file failed post processing test '{}'".format(outPath))
                return False
        else:
            self._log("Failed processing file '{}'".format(srcPath))
            return False
        # If file conversion was successful, we will get here
        self._log("Successfully processed file '{}'".format(srcPath))
        return True


    def generateFFMPEGArgs(self,input_file,output_file):
        ''' Build the ffmpeg conversion command and execute it

        @input_file : The absolute (full) path of the video file, string.
        @output_file : The absolute (full) path of temp conversion output file, string.
        '''
        # ffmpeg -i /library/XXXXX.mkv \
        #     -c:v libx265 \
        #     -map 0:0 -map 0:1 -map 0:1 \
        #     -c:a:0 copy \
        #     -c:a:1 libmp3lame -b:a:0 192k -ac 2 \
        #     -y /cache/XXXXX.mkv
        # 

        # Read video information for the input file
        file_properties = self.fileProbe(input_file)
        #if self.settings.DEBUGGING:
        #    self._log(json.dumps(file_properties,indent=2))

        # Build Command starting with specifying the input file
        command = ['-i',  input_file]

        # Set output
        #TODO: Check if we need '-nostats' here also
        command = command + ["-hide_banner", "-loglevel", "info", "-strict", "-2"]

        # Read stream data
        streams_to_map      = []
        streams_to_create   = []
        audio_tracks_count  = 0
        for stream in file_properties['streams']:
            if stream['codec_type'] == 'video':
                stream_data = stream
                # Map this stream
                streams_to_map = streams_to_map + [
                        "-map",   "0:{}".format(stream['index'])
                    ]

                streams_to_create = streams_to_create + [
                        "-c:v", self.settings.CODEC_CONFIG[self.settings.VIDEO_CODEC]['encoder']
                    ]
            if stream['codec_type'] == 'audio':
                # Get details of audio channel:
                if stream['channels'] > 2:
                    # Map this stream
                    streams_to_map = streams_to_map + [
                            "-map",   "0:{}".format(stream['index'])
                        ]

                    streams_to_create = streams_to_create + [
                            "-c:a:{}".format(audio_tracks_count), "copy"
                        ]
                    audio_tracks_count += 1

                    # TODO: Make this optional
                    try:
                        audio_tag = ''.join([i for i in stream['tags']['title'] if not i.isdigit()]).rstrip('.') + 'Stereo'
                    except:
                        audio_tag = 'Stereo'

                    # Map a duplicated stream
                    streams_to_map = streams_to_map + [
                            "-map",   " 0:{}".format(stream['index'])
                        ]

                    streams_to_create = streams_to_create + [
                                "-c:a:{}".format(audio_tracks_count), self.settings.CODEC_CONFIG[self.settings.AUDIO_CODEC]['encoder'] ,
                                "-b:a:{}".format(audio_tracks_count), self.settings.AUDIO_STEREO_STREAM_BITRATE,
                                "-ac", "2",
                                "-metadata:s:a:{}".format(audio_tracks_count), "title='{}'".format(audio_tag),
                            ]
                else:
                    # Force conversion of stereo audio to standard
                    streams_to_map = streams_to_map + [
                            "-map",   " 0:{}".format(stream['index'])
                        ]

                    streams_to_create = streams_to_create + [
                                "-c:a:{}".format(audio_tracks_count), self.settings.CODEC_CONFIG[self.settings.AUDIO_CODEC]['encoder'] ,
                                "-b:a:{}".format(audio_tracks_count), self.settings.AUDIO_STEREO_STREAM_BITRATE,
                                "-ac", "2",
                            ]
            if stream['codec_type'] == 'subtitle':
                if self.settings.REMOVE_SUBTITLE_STREAMS:
                    continue
                # Map this stream
                streams_to_map = streams_to_map + [
                        "-map",   "0:{}".format(stream['index'])
                    ]

                streams_to_create = streams_to_create + [
                        "-c:s:{}".format(audio_tracks_count), "copy"
                    ]
                audio_tracks_count += 1

        # Map streams
        command = command + streams_to_map

        # Add arguments for creating streams
        command = command + streams_to_create

        # Specify output file
        command = command + ["-y", output_file]

        if self.settings.DEBUGGING:
            self._log(" ".join(command))

        return command

    def execConvertFile(self, args):
        thread  = pexpect.spawn('ffmpeg', args)
        cpl     = thread.compile_pattern_list([
            pexpect.EOF,
            "Duration: (\d+):(\d+):(\d+)\.\d+",
            "(\d+\.\d+|\d+) fps",
            "frame= *.+",
        ])
        
        while True:
            i = thread.expect_list(cpl, timeout=None)
            if i == 0: # EOF
                # Process has exited
                break
            elif i == 1:
                # Set the total duration
                duration_string = thread.match.group(0).split()
                if not self.duration:
                    if len(duration_string) == 2:
                        self.duration = common.timestringToSeconds( duration_string[1].decode("utf-8") )
                    #self._log("Duration = {} seconds".format(self.duration))
                thread.close
            elif i == 2:
                # Set the source fps
                fps_string = thread.match.group(0).split()
                if not self.src_fps:
                    if len(fps_string) == 2:
                        self.src_fps = fps_string[0].decode("utf-8")
                    #self._log("FPS = {}".format(self.src_fps))
                thread.close
            elif i == 3:
                # Read encoding progress
                progress_string = thread.match.group(0)
                #self._log(progress_string)
                self.updateProgress(str(progress_string))
                thread.close
        return True

    def getProgressFromRegexOfString(self,line,regex_string,default=0):
        # Update frame
        regex   = re.compile(regex_string)
        search  = regex.search(line)
        if search:
            return_value = default
            split_list  = search.group(0).split('=')
            if len(split_list) == 2:
                return_value = split_list[1].strip()
            return return_value


    def updateProgress(self, progress_line):
        # 'frame=  167 fps= 11 q=-0.0 size=       3kB time=00:00:05.67 bitrate=   4.3kbits/s speed=0.371x'
        # Update percent and time
        regex_string    = "time=(\d+):(\d+):(\d+)\.\d+"
        time_string     = self.getProgressFromRegexOfString(progress_line,regex_string,self.percent)
        self.time       = common.timestringToSeconds(time_string)
        self.percent    = int(self.time / self.duration * 100)
        # Update frame
        self.frame  = self.getProgressFromRegexOfString(progress_line,"frame= *\d+",self.frame)
        # Update fps
        self.fps  = self.getProgressFromRegexOfString(progress_line,"fps= *\d+",self.fps)
        # Update speed
        self.speed  = self.getProgressFromRegexOfString(progress_line,"speed=(\d+\.\d+|\d+)",self.speed)
        # Update bitrate
        self.bitrate  = self.getProgressFromRegexOfString(progress_line,"bitrate= *([^\s]+)",self.bitrate)
        # Update file size
        self.file_size  = self.getProgressFromRegexOfString(progress_line,"size= *([^\s]+)",self.file_size)
        #self._log("time", self.time)
        #self._log("percent", self.percent)
        #self._log("frame", self.frame)
        #self._log("fps", self.fps)
        #self._log("speed", self.speed)
        #self._log("bitrate", self.bitrate)
        #self._log("file_size", self.file_size)





class TESTLOGGER(object):
    def put(self,message_dict):
        print(message_dict['level'] + ' - ', message_dict['message'], message_dict['message2'])

if __name__ == "__main__":
    ffmpeg  = FFMPEGHandle({}, TESTLOGGER())
    lib_dir = os.path.dirname(os.path.abspath(__file__))
    infile  = os.path.abspath(os.path.join(lib_dir,'..','tests','videos','bluedevils-large.mkv'))
    outfile = os.path.abspath(os.path.join(lib_dir,'..','tests','videos','bluedevils-large_out.mkv'))
    if not os.path.exists(infile):
        print("No such file: {}".format(infile))
        import sys
        sys.exit(1)
    if os.path.exists(outfile):
        os.remove(outfile)
    args = ['-i',
        infile,
        '-hide_banner',
        '-loglevel',
        'info',
        '-strict',
        '-2',
        '-map',
        '0:0',
        '-map',
        ' 0:1',
        '-c:v',
        'libx265',
        '-c:a:0',
        'aac',
        '-b:a:0',
        '128k',
        '-ac',
        '2',
        '-y',
        outfile]
    ffmpeg.execConvertFile(args)

