#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.metadata_api.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     03 Feb 2026

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

import tornado.log
from datetime import datetime

from unmanic.libs.metadata import UnmanicFileMetadata
from unmanic.libs.unmodels import CompletedTasks, FileMetadata, FileMetadataPaths
from peewee import fn
from unmanic.webserver.api_v2.base_api_handler import BaseApiError, BaseApiHandler
from unmanic.webserver.api_v2.schema.schemas import MetadataSearchResultsSchema, RequestMetadataSearchSchema, \
    RequestMetadataByTaskSchema, RequestMetadataUpdateSchema, RequestMetadataDeleteSchema, \
    RequestMetadataByFingerprintSchema, BaseSuccessSchema


class ApiMetadataHandler(BaseApiHandler):
    params = None
    routes = [
        {
            "path_pattern":      r"/metadata/search",
            "supported_methods": ["GET", "POST"],
            "call_method":       "search_metadata",
        },
        {
            "path_pattern":      r"/metadata/by-task",
            "supported_methods": ["POST"],
            "call_method":       "get_metadata_by_task",
        },
        {
            "path_pattern":      r"/metadata/by-fingerprint",
            "supported_methods": ["POST"],
            "call_method":       "get_metadata_by_fingerprint",
        },
        {
            "path_pattern":      r"/metadata/by-task/([0-9]+)",
            "supported_methods": ["GET"],
            "call_method":       "get_metadata_by_task_id",
        },
        {
            "path_pattern":      r"/metadata/update",
            "supported_methods": ["POST"],
            "call_method":       "update_metadata",
        },
        {
            "path_pattern":      r"/metadata",
            "supported_methods": ["DELETE"],
            "call_method":       "delete_metadata",
        },
    ]

    def initialize(self, **kwargs):
        self.params = kwargs.get("params")

    async def search_metadata(self):
        try:
            if self.request.method == 'GET':
                path = self.get_argument('path', None)
                offset = self.get_argument('offset', None)
                limit = self.get_argument('limit', None)
            else:
                json_request = self.read_json_request(RequestMetadataSearchSchema())
                path = json_request.get('path')
                offset = json_request.get('offset')
                limit = json_request.get('limit')

            try:
                offset = int(offset) if offset is not None else 0
            except Exception:
                offset = 0
            try:
                limit = int(limit) if limit is not None else 50
            except Exception:
                limit = 50

            if limit < 1:
                limit = 1
            if offset < 0:
                offset = 0

            results = []
            total_count = 0

            if not path:
                base = FileMetadata.select(FileMetadata.id)
                total_count = base.count()
                page_ids = [row.id for row in base.order_by(FileMetadata.updated_at.desc()).limit(limit).offset(offset)]
            else:
                search_value = path.strip().lower()
                base = (FileMetadata
                        .select(FileMetadata.id)
                        .join(FileMetadataPaths)
                        .where(fn.LOWER(FileMetadataPaths.path).contains(search_value))
                        .distinct())
                total_count = base.count()
                page_ids = [row.id for row in base.order_by(FileMetadata.updated_at.desc()).limit(limit).offset(offset)]

            if page_ids:
                path_map = {}
                for row in FileMetadataPaths.select().where(FileMetadataPaths.file_metadata.in_(page_ids)):
                    path_map.setdefault(row.file_metadata.id, []).append({
                        'path': row.path,
                        'path_type': row.path_type,
                    })

                for row in FileMetadata.select().where(FileMetadata.id.in_(page_ids)).order_by(FileMetadata.updated_at.desc()):
                    results.append({
                        'fingerprint': row.fingerprint,
                        'fingerprint_algo': row.fingerprint_algo,
                        'metadata_json': UnmanicFileMetadata._load_json_dict(row.metadata_json),
                        'last_task_id': row.last_task_id,
                        'paths': path_map.get(row.id, []),
                    })
            response = self.build_response(
                MetadataSearchResultsSchema(),
                {
                    "results": results,
                    "total_count": total_count,
                }
            )
            self.write_success(response)
            return
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def get_metadata_by_task(self):
        try:
            json_request = self.read_json_request(RequestMetadataByTaskSchema())
            task_id = json_request.get('task_id')
            await self._get_metadata_by_task_id(task_id)
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def get_metadata_by_task_id(self, task_id):
        try:
            await self._get_metadata_by_task_id(int(task_id))
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def _get_metadata_by_task_id(self, task_id):
        try:
            completed_task = CompletedTasks.get_by_id(task_id)
        except CompletedTasks.DoesNotExist:
            self.set_status(self.STATUS_ERROR_EXTERNAL, reason="Completed task not found")
            self.write_error()
            return

        path = completed_task.abspath
        metadata_ids = set()

        for row in FileMetadata.select(FileMetadata.id).where(FileMetadata.last_task_id == task_id):
            metadata_ids.add(row.id)

        for row in FileMetadataPaths.select(FileMetadataPaths.file_metadata).where(FileMetadataPaths.path == path):
            metadata_ids.add(row.file_metadata.id)

        results = []
        if metadata_ids:
            path_map = {}
            for row in FileMetadataPaths.select().where(FileMetadataPaths.file_metadata.in_(metadata_ids)):
                path_map.setdefault(row.file_metadata.id, []).append({
                    'path': row.path,
                    'path_type': row.path_type,
                })

            for row in FileMetadata.select().where(FileMetadata.id.in_(metadata_ids)):
                results.append({
                    'fingerprint': row.fingerprint,
                    'fingerprint_algo': row.fingerprint_algo,
                    'metadata_json': UnmanicFileMetadata._load_json_dict(row.metadata_json),
                    'last_task_id': row.last_task_id,
                    'paths': path_map.get(row.id, []),
                })

        response = self.build_response(
            MetadataSearchResultsSchema(),
            {
                "results": results,
                "total_count": len(results),
            }
        )
        self.write_success(response)

    async def update_metadata(self):
        try:
            json_request = self.read_json_request(RequestMetadataUpdateSchema())
            fingerprint = json_request.get('fingerprint')
            plugin_id = json_request.get('plugin_id')
            json_blob = json_request.get('json_blob')

            if not isinstance(json_blob, dict):
                self.set_status(self.STATUS_ERROR_EXTERNAL, reason="Metadata update requires a dict payload")
                self.write_error()
                return

            try:
                UnmanicFileMetadata._enforce_plugin_size_limit(json_blob)
            except ValueError as error:
                self.set_status(self.STATUS_ERROR_EXTERNAL, reason=str(error))
                self.write_error()
                return

            row = FileMetadata.get_or_none(FileMetadata.fingerprint == fingerprint)
            if not row:
                self.set_status(self.STATUS_ERROR_EXTERNAL, reason="Fingerprint not found")
                self.write_error()
                return

            data = UnmanicFileMetadata._load_json_dict(row.metadata_json)
            data[plugin_id] = json_blob
            row.metadata_json = UnmanicFileMetadata._dump_json_dict(data)
            row.updated_at = datetime.now()
            row.save()

            response = self.build_response(BaseSuccessSchema(), {"success": True})
            self.write_success(response)
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def delete_metadata(self):
        try:
            json_request = self.read_json_request(RequestMetadataDeleteSchema())
            fingerprint = json_request.get('fingerprint')
            plugin_id = json_request.get('plugin_id')

            result = UnmanicFileMetadata.delete_for_plugin(fingerprint, plugin_id=plugin_id)
            if not result:
                self.set_status(self.STATUS_ERROR_EXTERNAL, reason="Fingerprint not found")
                self.write_error()
                return

            response = self.build_response(BaseSuccessSchema(), {"success": True})
            self.write_success(response)
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()

    async def get_metadata_by_fingerprint(self):
        try:
            json_request = self.read_json_request(RequestMetadataByFingerprintSchema())
            fingerprint = json_request.get('fingerprint')
            if not fingerprint:
                self.set_status(self.STATUS_ERROR_EXTERNAL, reason="Fingerprint not provided")
                self.write_error()
                return

            row = FileMetadata.get_or_none(FileMetadata.fingerprint == fingerprint)
            results = []
            if row:
                path_map = []
                for path_row in FileMetadataPaths.select().where(FileMetadataPaths.file_metadata == row.id):
                    path_map.append({
                        'path': path_row.path,
                        'path_type': path_row.path_type,
                    })

                results.append({
                    'fingerprint': row.fingerprint,
                    'fingerprint_algo': row.fingerprint_algo,
                    'metadata_json': UnmanicFileMetadata._load_json_dict(row.metadata_json),
                    'last_task_id': row.last_task_id,
                    'paths': path_map,
                })

            response = self.build_response(
                MetadataSearchResultsSchema(),
                {
                    "results": results,
                    "total_count": len(results),
                }
            )
            self.write_success(response)
        except BaseApiError as bae:
            tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
            return
        except Exception as e:
            self.set_status(self.STATUS_ERROR_INTERNAL, reason=str(e))
            self.write_error()
