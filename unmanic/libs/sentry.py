#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import json
import logging
import os
from typing import Dict, Any, Optional, TypedDict
from urllib.parse import urlparse

from unmanic import metadata
from unmanic.libs.logs import UnmanicLogging

sentry_logger = UnmanicLogging.get_logger(name="Unmanic.Sentry")


class SentryRuntimeConfig(TypedDict):
    SENTRY_DEBUG: bool
    SENTRY_DOCKER_IMAGE_TAG: str
    SENTRY_DSN: str
    SENTRY_ENVIRONMENT: str
    SENTRY_HOSTNAME: Optional[str]
    SENTRY_PROFILES_SAMPLE_RATE: float
    SENTRY_RELEASE: str
    SENTRY_SERVICE_NAME: str
    SENTRY_TRANSPORT_TIMEOUT: float
    SENTRY_TRACES_SAMPLE_RATE: float
    enable_tracing: bool


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _parse_sentry_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _parse_sentry_float(value: Any, default: float) -> Optional[float]:
    if value in (None, ""):
        return default
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_sentry_json_config() -> Dict[str, Any]:
    raw_sentry_config = os.environ.get("SENTRY_CONFIG", "")
    if len(raw_sentry_config) <= 10:
        if os.environ.get("SENTRY_CONFIG"):
            sentry_logger.warning("Ignoring SENTRY_CONFIG because it is too short to be valid JSON")
        return {}

    try:
        parsed_sentry_config = json.loads(raw_sentry_config)
    except json.JSONDecodeError:
        sentry_logger.warning("Ignoring SENTRY_CONFIG because it is not valid JSON")
        return {}

    if not isinstance(parsed_sentry_config, dict):
        sentry_logger.warning("Ignoring SENTRY_CONFIG because it is not a JSON object")
        return {}

    return parsed_sentry_config


def _get_build_version() -> str:
    version_str = metadata.read_version_string("long")
    if version_str:
        return version_str
    return "unknown"


def _load_sentry_config() -> Optional[SentryRuntimeConfig]:
    parsed_sentry_config = _load_sentry_json_config()
    if parsed_sentry_config:
        sentry_logger.info(
            "Detected SENTRY_CONFIG JSON with keys: %s",
            ", ".join(sorted(parsed_sentry_config.keys())),
        )
    elif os.environ.get("SENTRY_DSN"):
        sentry_logger.info("Detected SENTRY_DSN environment variable")

    def _config_value(name: str, default: Any = None) -> Any:
        return parsed_sentry_config.get(name, os.environ.get(name, default))

    dsn = _config_value("SENTRY_DSN")
    if not isinstance(dsn, str) or not _is_valid_url(dsn):
        if parsed_sentry_config or os.environ.get("SENTRY_DSN"):
            sentry_logger.warning("Ignoring Sentry configuration because SENTRY_DSN is missing or invalid")
        return None

    traces_sample_rate = _parse_sentry_float(_config_value("SENTRY_TRACES_SAMPLE_RATE"), 0.2)
    profiles_sample_rate = _parse_sentry_float(_config_value("SENTRY_PROFILES_SAMPLE_RATE"), 0.2)
    tracing_enabled = (
        traces_sample_rate is not None
        and profiles_sample_rate is not None
        and traces_sample_rate > 0
        and profiles_sample_rate > 0
    )

    if not tracing_enabled:
        sentry_logger.warning(
            "SENTRY_CONFIG tracing disabled because one or more sample rates are missing, invalid, or non-positive"
        )

    sentry_traces_sample_rate: float = 0.0
    sentry_profiles_sample_rate: float = 0.0
    if tracing_enabled:
        assert traces_sample_rate is not None
        assert profiles_sample_rate is not None
        sentry_traces_sample_rate = traces_sample_rate
        sentry_profiles_sample_rate = profiles_sample_rate

    sentry_runtime_config: SentryRuntimeConfig = {
        "SENTRY_DEBUG": _parse_sentry_bool(_config_value("SENTRY_DEBUG"), default=False),
        "SENTRY_DOCKER_IMAGE_TAG": str(_config_value("SENTRY_DOCKER_IMAGE_TAG", "") or ""),
        "SENTRY_DSN": dsn,
        "enable_tracing": tracing_enabled,
        "SENTRY_ENVIRONMENT": str(_config_value("SENTRY_ENVIRONMENT", "production") or "production"),
        "SENTRY_HOSTNAME": str(_config_value("SENTRY_HOSTNAME", "") or "") or None,
        "SENTRY_PROFILES_SAMPLE_RATE": sentry_profiles_sample_rate,
        "SENTRY_RELEASE": str(_config_value("SENTRY_RELEASE", _get_build_version()) or _get_build_version()),
        "SENTRY_SERVICE_NAME": str(_config_value("SENTRY_SERVICE_NAME", "unmanic") or "unmanic"),
        "SENTRY_TRANSPORT_TIMEOUT": _parse_sentry_float(_config_value("SENTRY_TRANSPORT_TIMEOUT"), 30.0) or 30.0,
        "SENTRY_TRACES_SAMPLE_RATE": sentry_traces_sample_rate,
    }
    sentry_logger.info(
        "Sentry runtime config accepted: environment=%s release=%s tracing=%s debug=%s service_name=%s transport_timeout=%ss",
        sentry_runtime_config["SENTRY_ENVIRONMENT"],
        sentry_runtime_config["SENTRY_RELEASE"],
        "enabled" if sentry_runtime_config["enable_tracing"] else "disabled",
        sentry_runtime_config["SENTRY_DEBUG"],
        sentry_runtime_config["SENTRY_SERVICE_NAME"],
        sentry_runtime_config["SENTRY_TRANSPORT_TIMEOUT"],
    )
    return sentry_runtime_config


def initialise_sentry():
    sentry_runtime_config = _load_sentry_config()
    if not sentry_runtime_config:
        sentry_logger.info("Sentry is disabled for this process")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.tornado import TornadoIntegration
        from sentry_sdk.transport import HttpTransport
    except ImportError:
        sentry_logger.warning("SENTRY_CONFIG or SENTRY_DSN is set but sentry-sdk is not installed")
        return

    transport_timeout = max(float(sentry_runtime_config["SENTRY_TRANSPORT_TIMEOUT"]), 0.1)

    class ConfiguredHttpTransport(HttpTransport):
        TIMEOUT = transport_timeout

    sentry_logger.info("Initialising sentry-sdk with Tornado and logging integrations")
    sentry_sdk.init(
        dsn=sentry_runtime_config["SENTRY_DSN"],
        debug=sentry_runtime_config["SENTRY_DEBUG"],
        enable_tracing=sentry_runtime_config["enable_tracing"],
        environment=sentry_runtime_config["SENTRY_ENVIRONMENT"],
        integrations=[
            TornadoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        profiles_sample_rate=sentry_runtime_config["SENTRY_PROFILES_SAMPLE_RATE"],
        release=sentry_runtime_config["SENTRY_RELEASE"],
        server_name=sentry_runtime_config["SENTRY_HOSTNAME"],
        transport=ConfiguredHttpTransport,
        traces_sample_rate=sentry_runtime_config["SENTRY_TRACES_SAMPLE_RATE"],
    )

    sentry_sdk.set_tag("service_name", sentry_runtime_config["SENTRY_SERVICE_NAME"])
    docker_image_tag = sentry_runtime_config["SENTRY_DOCKER_IMAGE_TAG"]
    if docker_image_tag:
        sentry_sdk.set_tag("docker_image_tag", docker_image_tag)
    if sentry_runtime_config["SENTRY_DEBUG"]:
        sentry_logger.info("SENTRY_DEBUG is enabled; sending bootstrap test message")
        sentry_sdk.capture_message("Unmanic Sentry bootstrap test", level="info")
        sentry_logger.info("Bootstrap test message submitted to sentry-sdk")
    sentry_logger.info("sentry-sdk initialised successfully")
