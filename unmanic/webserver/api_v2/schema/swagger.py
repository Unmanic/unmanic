#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.swagger.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     01 Aug 2021, (9:50 AM)

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
import importlib
import json
import os

import yaml
from apispec import APISpec
from apispec.exceptions import APISpecError
from apispec.ext.marshmallow import MarshmallowPlugin

from unmanic.webserver.api_v2 import list_all_handlers
from unmanic.webserver.api_v2.schema.unmanic import UnmanicSpecPlugin

API_VERSION = "2"
OPENAPI_SPEC_SECURITY = """
components:
  securitySchemes:
    BasicAuth:
      type: http
      scheme: basic
security:
  - BasicAuth: []
"""


def find_all_handlers():
    return_list = []
    for handler in list_all_handlers():
        endpoint_handler = getattr(importlib.import_module("unmanic.webserver.api_v2"), handler)
        for route in endpoint_handler.routes:
            path_pattern = route.get('path_pattern')
            return_list.append(
                (path_pattern, endpoint_handler,)
            )
    return return_list


def generate_swagger_file():
    """Automatically generates Swagger spec file based on RequestHandler
    docstrings and saves it to the specified file_location.
    """
    errors = []

    file_location = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'api_schema_v{}'.format(API_VERSION))

    # Starting to generate Swagger spec file. All the relevant
    # information can be found from here https://apispec.readthedocs.io/
    security_settings = yaml.safe_load(OPENAPI_SPEC_SECURITY)
    spec = APISpec(
        title="Unmanic API",
        version=str(API_VERSION),
        openapi_version="3.0.0",
        info=dict(description="Documentation for the Unmanic application API"),
        plugins=[UnmanicSpecPlugin(), MarshmallowPlugin()],
        servers=[
            {"url": "http://localhost:8888/unmanic/api/v{}/".format(API_VERSION), "description": "Local environment", },
        ],
        **security_settings
    )
    # Looping through all the handlers and trying to register them.
    # Handlers without docstring will raise errors. That's why we
    # are catching them silently.
    handlers = find_all_handlers()
    for handler in handlers:
        try:
            spec.path(urlspec=handler)
        except APISpecError as e:
            errors.append("API Docs - Failed to append spec path - {}".format(str(e)))
            pass

    # Write the Swagger file into specified location.
    with open('{}.json'.format(file_location), "w", encoding="utf-8") as file:
        json.dump(spec.to_dict(), file, ensure_ascii=False, indent=4)
    # TODO: Remove YAML. It sucks!
    with open('{}.yaml'.format(file_location), "w", encoding="utf-8") as file:
        file.write(spec.to_yaml())

    return errors
