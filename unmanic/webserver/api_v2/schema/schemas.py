#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.schemas.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     01 Aug 2021, (11:45 AM)

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
from marshmallow import Schema, fields, validate


class BaseSchema(Schema):
    class Meta:
        ordered = True


# RESPONSES
# =========

class BaseSuccessSchema(BaseSchema):
    success = fields.Boolean(
        required=True,
        description='This is always "True" when a request succeeds',
        example=True,
    )


class BaseErrorSchema(BaseSchema):
    error = fields.Str(
        required=True,
        description="Return status code and reason",
    )
    messages = fields.Dict(
        required=True,
        description="Attached request body validation errors",
        example={"name": ["The thing that went wrong."]},
    )
    traceback = fields.List(
        cls_or_instance=fields.Str,
        required=False,
        description="Attached exception traceback (if developer mode is enabled)",
        example=[
            "Traceback (most recent call last):\n",
            "...",
            "json.decoder.JSONDecodeError: Expecting value: line 3 column 14 (char 45)\n"
        ],
    )


class BadRequestSchema(BaseErrorSchema):
    """STATUS_ERROR_EXTERNAL = 400"""
    error = fields.Str(
        required=True,
        description="Return status code and reason",
        example="400: Failed request schema validation",
    )


class BadEndpointSchema(BaseSchema):
    """STATUS_ERROR_ENDPOINT_NOT_FOUND = 404"""
    error = fields.Str(
        required=True,
        description="Return status code and reason",
        example="404: Endpoint not found",
    )


class BadMethodSchema(BaseSchema):
    """STATUS_ERROR_METHOD_NOT_ALLOWED = 405"""
    error = fields.Str(
        required=True,
        description="Return status code and reason",
        example="405: Method 'GET' not allowed",
    )


class InternalErrorSchema(BaseErrorSchema):
    """STATUS_ERROR_INTERNAL = 500"""
    error = fields.Str(
        required=True,
        description="Return status code and reason",
        example="500: Caught exception message",
    )


# GENERIC
# =======

class RequestTableDataSchema(BaseSchema):
    """Table request schema"""

    start = fields.Int(
        required=False,
        description="Start row number to select from",
        example=0,
        load_default=0,
    )
    length = fields.Int(
        required=False,
        description="Number of rows to select",
        example=10,
        load_default=10,
    )
    search_value = fields.Str(
        required=False,
        description="String to filter search results by",
        example="items with this text in the value",
        load_default="",
    )
    order_by = fields.Str(
        required=False,
        description="Column to order results by",
        example="finish_time",
        load_default="",
    )
    order_direction = fields.Str(
        required=False,
        description="Order direction ('asc' or 'desc')",
        example="desc",
        validate=validate.OneOf(["asc", "desc"]),
    )


class RequestTableUpdateByIdList(BaseSchema):
    """Schema for updating tables by ID"""

    id_list = fields.List(
        cls_or_instance=fields.Int,
        required=True,
        description="List of table IDs",
        example=[],
        validate=validate.Length(min=1),
    )


class TableRecordsSuccessSchema(BaseSchema):
    """Schema for table results"""

    recordsTotal = fields.Int(
        required=False,
        description="Total number of records in this table",
        example=329,
    )
    recordsFiltered = fields.Int(
        required=False,
        description="Total number of records after filters have been applied",
        example=10,
        load_default=10,
    )
    results = fields.List(
        cls_or_instance=fields.Raw,
        required=False,
        description="Results",
        example=[],
    )


# DOCS
# ====

class DocumentContentSuccessSchema(BaseSchema):
    """Schema for updating tables by ID"""

    content = fields.List(
        cls_or_instance=fields.Str,
        required=True,
        description="Document contents read line-by-line into a list",
        example=[
            "First line\n",
            "Second line\n",
            "\n",
        ],
        validate=validate.Length(min=1),
    )


# FILEBROWSER
# ===========

class RequestDirectoryListingDataSchema(BaseSchema):
    """Schema for requesting a directory content listing"""

    current_path = fields.Str(
        example="/",
        load_default="/",
    )
    list_type = fields.Str(
        example="directories",
        load_default="all",
    )


class DirectoryListingResultsSchema(BaseSchema):
    """Schema for directory listing results returned"""

    directories = fields.List(
        cls_or_instance=fields.Dict,
        required=True,
        description="A list of directories in the given path",
        example=[
            {
                'value': "home",
                'label': "/home",
            },
            {
                'value': "tmp",
                'label': "/tmp",
            },
        ],
        validate=validate.Length(min=0),
    )
    files = fields.List(
        cls_or_instance=fields.Dict,
        required=True,
        description="A list of files in the given path",
        example=[
            {
                'value': "file1.txt",
                'label': "/file1.txt",
            },
            {
                'value': "file2.txt",
                'label': "/file2.txt",
            },
        ],
        validate=validate.Length(min=0),
    )


# HISTORY
# =======

class RequestHistoryTableDataSchema(RequestTableDataSchema):
    """Schema for requesting completed tasks from the table"""

    order_by = fields.Str(
        example="finish_time",
        load_default="finish_time",
    )


class CompletedTasksTableResultsSchema(BaseSchema):
    """Schema for completed tasks results returned by the table"""

    id = fields.Int(
        required=True,
        description="Item ID",
        example=1,
    )
    task_label = fields.Str(
        required=True,
        description="Item label",
        example="example.mp4",
    )
    task_success = fields.Boolean(
        required=True,
        description="Item success status",
        example=True,
    )
    finish_time = fields.Int(
        required=True,
        description="Item finish time",
        example=1627392616.6400812,
    )


class CompletedTasksSchema(TableRecordsSuccessSchema):
    """Schema for returning a list of completed task results"""

    successCount = fields.Int(
        required=True,
        description="Total count of times with a success status in the results list",
        example=337,
    )
    failedCount = fields.Int(
        required=True,
        description="Total count of times with a failed status in the results list",
        example=2,
    )
    results = fields.Nested(
        CompletedTasksTableResultsSchema,
        required=True,
        description="Results",
        many=True,
        validate=validate.Length(min=0),
    )


class CompletedTasksLogRequestSchema(BaseSchema):
    """Schema for requesting a task log"""

    task_id = fields.Int(
        required=True,
        description="The ID of the task",
        example=1,
    )


class CompletedTasksLogSchema(BaseSchema):
    """Schema for returning a list of completed task results"""

    command_log = fields.Str(
        required=True,
        description="Long string...",
        example='Long string...',
    )
    command_log_lines = fields.List(
        cls_or_instance=fields.Str,
        required=True,
        description="The long string broken up into an array of lines",
        example=[
            "",
            "<b>RUNNER: </b>",
            "Video Encoder H264 - libx264 [Pass #1]",
            "",
            "<b>COMMAND:</b>",
            "",
            "...",
        ],
    )


# PENDING
# =======

class RequestPendingTableDataSchema(RequestTableDataSchema):
    """Schema for requesting pending tasks from the table"""

    order_by = fields.Str(
        example="priority",
        load_default="priority",
    )


class PendingTasksTableResultsSchema(BaseSchema):
    """Schema for pending task results returned by the table"""

    id = fields.Int(
        required=True,
        description="Item ID",
        example=1,
    )
    abspath = fields.Str(
        required=True,
        description="File absolute path",
        example="example.mp4",
    )
    priority = fields.Int(
        required=True,
        description="The current priority (higher is greater)",
        example=100,
    )
    status = fields.Str(
        required=True,
        description="The current status of the pending task",
        example="pending",
    )


class PendingTasksSchema(TableRecordsSuccessSchema):
    """Schema for returning a list of pending task results"""

    results = fields.Nested(
        PendingTasksTableResultsSchema,
        required=True,
        description="Results",
        many=True,
        validate=validate.Length(min=0),
    )


class RequestPendingTasksReorderSchema(RequestTableUpdateByIdList):
    """Schema for moving pending items to top or bottom of table by ID"""

    position = fields.Str(
        required=True,
        description="Position to move given list of items to ('top' or 'bottom')",
        example="top",
        validate=validate.OneOf(["top", "bottom"]),
    )


# PLUGINS
# =======

class RequestPluginsTableDataSchema(RequestTableDataSchema):
    """Schema for requesting plugins from the table"""

    order_by = fields.Str(
        example="name",
        load_default="name",
    )


class PluginStatusSchema(BaseSchema):
    installed = fields.Boolean(
        required=False,
        description="Is the plugin installed",
        example=True,
    )
    enabled = fields.Boolean(
        required=False,
        description="Is the plugin enabled",
        example=True,
    )
    update_available = fields.Boolean(
        required=False,
        description="Does the plugin have an update available",
        example=True,
    )


class RequestPluginsByIdSchema(BaseSchema):
    """Schema to request data pertaining to a plugin by it's Plugin ID"""

    plugin_id = fields.Str(
        required=True,
        example="dts_to_dd",
    )


class PluginsMetadataResultsSchema(BaseSchema):
    """Schema for plugin metadata that will be returned by various requests """

    plugin_id = fields.Str(
        required=True,
        description="The plugin ID",
        example="encoder_video_h264_nvenc",
    )
    name = fields.Str(
        required=True,
        description="The plugin name",
        example="Video Encoder H264 - h264_nvenc",
    )
    author = fields.Str(
        required=True,
        description="The plugin author",
        example="encoder_video_h264_nvenc",
    )
    description = fields.Str(
        required=True,
        description="The plugin description",
        example="Ensure all video streams are encoded with the H264 codec using the h264_nvenc encoder.",
    )
    version = fields.Str(
        required=True,
        description="The plugin version",
        example="Josh.5",
    )
    icon = fields.Str(
        required=True,
        description="The plugin icon",
        example="https://raw.githubusercontent.com/Josh5/unmanic-plugins/master/source/encoder_video_h264_nvenc/icon.png",
    )
    tags = fields.Str(
        required=True,
        description="The plugin tags",
        example="video,encoder,ffmpeg,worker,nvenc,nvdec,nvidia",
    )
    status = fields.Nested(
        PluginStatusSchema,
        required=True,
        description="The plugin status",
    )
    changelog = fields.Str(
        required=False,
        description="The plugin changelog",
        example="[b][color=56adda]0.0.1[/color][/b]• initial version",
    )


class PluginsTableResultsSchema(PluginsMetadataResultsSchema):
    """Schema for pending task results returned by the table"""

    id = fields.Int(
        required=True,
        description="Item table ID",
        example=1,
    )


class PluginsDataSchema(TableRecordsSuccessSchema):
    """Schema for returning a list of plugin table results"""

    results = fields.Nested(
        PluginsTableResultsSchema,
        required=True,
        description="Results",
        many=True,
        validate=validate.Length(min=0),
    )


class RequestPluginsInfoSchema(RequestPluginsByIdSchema):
    """Schema for requesting plugins info by a given Plugin ID"""

    prefer_local = fields.Boolean(
        required=False,
        load_default=True,
        example=True,
    )


class PluginsConfigInputItemSchema(BaseSchema):
    """Schema for plugin config input items"""

    key_id = fields.Str(
        required=True,
        description="The config input base64 encoded key (used for linking keys containing spaces, etc.)",
        example="c8f122656ed2acabde9b57101a4c8ec7",
    )
    key = fields.Str(
        required=True,
        description="The config input key or name",
        example="downmix_dts_hd_ma",
    )
    value = fields.Raw(
        required=True,
        description="The current value of this config input",
        example=False,
    )
    input_type = fields.Str(
        required=True,
        description="The config input type",
        example="checkbox",
    )
    label = fields.Str(
        required=True,
        description="The label used to define this config input",
        example="Downmix DTS-HD Master Audio (max 5.1 channels)?",
    )
    select_options = fields.List(
        cls_or_instance=fields.Dict,
        required=True,
        description="Additional options if the input_type is set to 'select'",
        example=[
            {
                'value': "first",
                'label': "First Option",
            },
            {
                'value': "second",
                'label': "Second Option",
            },
        ],
    )
    slider_options = fields.Dict(
        required=True,
        description="Additional options if the input_type is set to 'slider'",
        example={
            "min":    1,
            "max":    8,
            "suffix": "M"
        },
    )
    display = fields.Str(
        required=True,
        description="Should the setting input be displayed (visible, hidden)",
        example="visible",
    )


class PluginsInfoResultsSchema(PluginsMetadataResultsSchema):
    """Schema for pending task results returned by the table"""

    settings = fields.Nested(
        PluginsConfigInputItemSchema,
        required=False,
        many=True,
        description="The plugin settings",
    )


class RequestPluginsSettingsSaveSchema(BaseSchema):
    """Schema for requesting the update of a plugins settings by the plugin install ID"""

    plugin_id = fields.Str(
        required=True,
        example="dts_to_dd",
    )
    settings = fields.Nested(
        PluginsConfigInputItemSchema,
        required=True,
        many=True,
        description="The plugin settings",
    )


class PluginsMetadataInstallableResultsSchema(PluginsMetadataResultsSchema):
    """Schema for plugin metadata that will be returned when fetching installable plugins """

    package_url = fields.Str(
        required=False,
        description="The plugin package download URL",
        example="https://raw.githubusercontent.com/Unmanic/unmanic-plugins/repo/plugin_id/plugin_id-1.0.0.zip",
    )
    changelog_url = fields.Str(
        required=False,
        description="The plugin package download URL",
        example="https://raw.githubusercontent.com/Unmanic/unmanic-plugins/repo/plugin_id/changelog.md",
    )


class PluginsInstallableResultsSchema(BaseSchema):
    """Schema for installable plugins lists that are returned"""

    plugins = fields.Nested(
        PluginsMetadataInstallableResultsSchema,
        required=True,
        description="Results",
        many=True,
        validate=validate.Length(min=0),
    )


class PluginTypesResultsSchema(BaseSchema):
    """Schema for installable plugins lists that are returned"""

    results = fields.List(
        cls_or_instance=fields.Str,
        required=True,
        description="List of Plugin Type IDs supported by this installation",
        example=[
            "library_management.file_test",
            "postprocessor.file_move",
            "postprocessor.task_result",
            "worker.process_item"
        ],
    )


class RequestPluginsFlowByPluginTypeSchema(BaseSchema):
    """Schema to request the plugin flow of a given plugin type"""

    plugin_type = fields.Str(
        required=True,
        example="library_management.file_test",
    )


class PluginFlowDataResultsSchema(BaseSchema):
    """Schema for plugin flow data items"""

    plugin_id = fields.Str(
        required=True,
        description="The plugin ID",
        example="encoder_video_h264_nvenc",
    )
    name = fields.Str(
        required=True,
        description="The plugin name",
        example="Video Encoder H264 - h264_nvenc",
    )
    author = fields.Str(
        required=True,
        description="The plugin author",
        example="encoder_video_h264_nvenc",
    )
    description = fields.Str(
        required=True,
        description="The plugin description",
        example="Ensure all video streams are encoded with the H264 codec using the h264_nvenc encoder.",
    )
    version = fields.Str(
        required=True,
        description="The plugin version",
        example="Josh.5",
    )
    icon = fields.Str(
        required=True,
        description="The plugin icon",
        example="https://raw.githubusercontent.com/Josh5/unmanic-plugins/master/source/encoder_video_h264_nvenc/icon.png",
    )


class PluginFlowResultsSchema(BaseSchema):
    """Schema for returned plugin flow list"""

    results = fields.Nested(
        PluginFlowDataResultsSchema,
        required=True,
        description="Results",
        many=True,
        validate=validate.Length(min=0),
    )


class RequestSavingPluginsFlowByPluginTypeSchema(RequestPluginsFlowByPluginTypeSchema):
    """Schema to request saving the plugin flow of a given plugin type"""

    plugin_flow = fields.Nested(
        PluginFlowDataResultsSchema,
        required=True,
        description="Saved flow",
        many=True,
        validate=validate.Length(min=1),
    )


class PluginReposMetadataResultsSchema(BaseSchema):
    """Schema for plugin repo metadata that will be returned when fetching repo lists"""

    id = fields.Str(
        required=True,
        description="The plugin repo ID",
        example="repository.josh5",
    )
    name = fields.Str(
        required=True,
        description="The plugin repo name",
        example="Josh.5 Development Plugins for Unmanic",
    )
    icon = fields.Str(
        required=True,
        description="The plugin repo icon",
        example="https://raw.githubusercontent.com/Josh5/unmanic-plugins/master/icon.png",
    )
    path = fields.Str(
        required=True,
        description="The plugin repo URL path",
        example="https://raw.githubusercontent.com/Josh5/unmanic-plugins/repo/repo.json",
    )


class RequestUpdatePluginReposListSchema(BaseSchema):
    """Schema to request an update of the plugin repos list"""

    repos_list = fields.List(
        cls_or_instance=fields.Str,
        required=True,
        description="A list of repost to save",
        example=[
            'https://raw.githubusercontent.com/Josh5/unmanic-plugins/repo/repo.json',
        ],
        validate=validate.Length(min=0),
    )


class PluginReposListResultsSchema(BaseSchema):
    """Schema for plugin repo lists that are returned"""

    repos = fields.Nested(
        PluginReposMetadataResultsSchema,
        required=True,
        description="Results",
        many=True,
        validate=validate.Length(min=0),
    )


class PluginsDataPanelTypesDataSchema(BaseSchema):
    """Schema for returning a list of data panel plugins results"""

    results = fields.Nested(
        PluginFlowDataResultsSchema,
        required=True,
        description="Results",
        many=True,
        validate=validate.Length(min=0),
    )


# SESSION
# =======

class SessionStateSuccessSchema(BaseSchema):
    """Schema for returning session data"""

    level = fields.Int(
        required=True,
        description="User level",
        example=0,
    )
    picture_uri = fields.Str(
        required=False,
        description="User picture",
        example="https://c8.patreon.com/2/200/561356054",
    )
    name = fields.Str(
        required=False,
        description="User name",
        example="ExampleUsername123",
    )
    email = fields.Str(
        required=False,
        description="User email",
        example="example@gmail.com",
    )
    created = fields.Number(
        required=False,
        description="Session time created",
        example=1627793093.676484,
    )
    uuid = fields.Str(
        required=True,
        description="Installation uuid",
        example="b429fcc7-9ce1-bcb3-2b8a-b094747f226e",
    )


# SETTINGS
# ========

class SettingsReadAndWriteSchema(BaseSchema):
    """Schema to request the current settings"""

    settings = fields.Dict(
        required=True,
        description="The current settings",
        example={
            "ui_port":                    8888,
            "debugging":                  False,
            "library_path":               "/library",
            "enable_library_scanner":     False,
            "schedule_full_scan_minutes": 1440,
            "follow_symlinks":            True,
            "run_full_scan_on_start":     False,
            "enable_inotify":             False,
            "number_of_workers":          1,
            "cache_path":                 "/tmp/unmanic"
        },
    )

class SettingsSystemConfigSchema(BaseSchema):
    """Schema to display the current system configuration"""

    configuration = fields.Dict(
        required=True,
        description="The current system configuration",
        example={},
    )


# VERSION
# =======

class VersionReadSuccessSchema(BaseSchema):
    """Schema for returning the application version"""

    version = fields.Str(
        required=True,
        description="Application version",
        example="1.0.0",
    )


# WORKERS
# =======

class RequestWorkerByIdSchema(BaseSchema):
    """Schema to request a worker by the worker's ID"""

    worker_id = fields.Str(
        required=True,
        example="1",
    )
