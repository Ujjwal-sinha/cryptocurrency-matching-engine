"""
Configuration module for the matching engine.

This module provides configuration management and settings
for the cryptocurrency matching engine.
"""

from .settings import Settings, get_settings

__all__ = [
    "Settings",
    "get_settings",
]
