"""
Environment configuration loader.

Loads and validates configuration from Pulumi stack config files.
"""

import pulumi

from IAC.configs.base import EnvironmentConfig


def get_config() -> EnvironmentConfig:
    """
    Load environment configuration from Pulumi stack config.

    Returns:
        EnvironmentConfig: Validated configuration object

    Raises:
        pulumi.ConfigMissingError: If required config values are missing
    """
    config = pulumi.Config()

    return EnvironmentConfig(
        environment=config.require("environment"),
        domain=config.require("domain"),
        ec2_instance_type=config.get("ec2_instance_type") or "t3.small",
        rds_instance_class=config.get("rds_instance_class") or "db.t3.micro",
        rds_allocated_storage=int(config.get("rds_allocated_storage") or "20"),
        lambda_memory=int(config.get("lambda_memory") or "512"),
        lambda_timeout=int(config.get("lambda_timeout") or "300"),
        enable_deletion_protection=config.get_bool("enable_deletion_protection") or False,
        multi_az=config.get_bool("multi_az") or False,
    )
