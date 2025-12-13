"""
Configuration module for Pulumi infrastructure.

Provides type-safe configuration loading from Pulumi stack config files.
"""

from IAC.configs.base import EnvironmentConfig
from IAC.configs.environment import get_config
from IAC.configs.constants import (
    VPC_CIDR,
    SUBNET_CIDRS,
    DEFAULT_TAGS,
    INSTANCE_TYPES,
)

__all__ = [
    "EnvironmentConfig",
    "get_config",
    "VPC_CIDR",
    "SUBNET_CIDRS",
    "DEFAULT_TAGS",
    "INSTANCE_TYPES",
]
