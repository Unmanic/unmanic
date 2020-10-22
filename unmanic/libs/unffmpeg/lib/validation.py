#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.validation.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     22 Oct 2020, (7:45 PM)

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

command_schema = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "$id": "http://example.com/example.json",
    "type": "object",
    "title": "The root schema",
    "description": "The root schema comprises the entire JSON document.",
    "default": {},
    "required": [
        "ffmpeg",
        "-i",
    ],
    "properties": {
        "ffmpeg": {
            "type": "string",
            "title": "The main command.",
            "description": "The main command."
        },
        "-i": {
            "type": "string",
            "title": "The main command.",
            "description": "The main command.",
            "minLength": 1
        },
        "-hide_banner": {
            "type": "string",
            "title": "The -hide_banner schema",
            "description": "An explanation about the purpose of this instance.",
            "default": "",
            "examples": [
                ""
            ]
        },
        "-loglevel": {
            "type": "string",
            "title": "The -loglevel schema",
            "description": "An explanation about the purpose of this instance.",
            "default": "info",
            "examples": [
                "info",
                "warning",
                "debug",
                "verbose"
            ]
        },
        "-max_muxing_queue_size": {
            "type": "string",
            "title": "The -max_muxing_queue_size schema",
            "description": "An explanation about the purpose of this instance.",
            "default": "512",
            "examples": [
                "512"
            ]
        }
    },
    "additionalProperties": True
}
