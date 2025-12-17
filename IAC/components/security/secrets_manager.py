"""
Secrets Manager component for API keys and credentials.

Creates secrets for:
- Google API key (embeddings)
- Anthropic API key (Claude completions)
- Database credentials (RDS PostgreSQL)
"""

import json

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags
from IAC.utils.naming import ResourceNamer


class SecretsManagerComponent(pulumi.ComponentResource):
    """
    Secrets Manager component for storing sensitive configuration.

    Secrets are created with placeholder values that should be
    populated manually or via CI/CD pipeline.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        namer: ResourceNamer,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:security:SecretsManager", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # Google API Key secret
        self.google_api_key = aws.secretsmanager.Secret(
            f"{name}-google-api-key",
            name=namer.secret_name("google-api-key-v3"),
            description="Google API key for text-embedding-004",
            recovery_window_in_days=0,  # Immediate deletion (dev only)
            tags=create_tags(environment, f"{name}-google-api-key"),
            opts=child_opts,
        )

        # Set placeholder version (actual value set via console/CLI)
        aws.secretsmanager.SecretVersion(
            f"{name}-google-api-key-version",
            secret_id=self.google_api_key.id,
            secret_string=json.dumps({"api_key": "PLACEHOLDER_SET_VIA_CLI"}),
            opts=child_opts,
        )

        # Anthropic API Key secret
        self.anthropic_api_key = aws.secretsmanager.Secret(
            f"{name}-anthropic-api-key",
            name=namer.secret_name("anthropic-api-key-v3"),
            description="Anthropic API key for Claude completions",
            recovery_window_in_days=0,  # Immediate deletion (dev only)
            tags=create_tags(environment, f"{name}-anthropic-api-key"),
            opts=child_opts,
        )

        aws.secretsmanager.SecretVersion(
            f"{name}-anthropic-api-key-version",
            secret_id=self.anthropic_api_key.id,
            secret_string=json.dumps({"api_key": "PLACEHOLDER_SET_VIA_CLI"}),
            opts=child_opts,
        )

        # Database credentials secret (with random password)
        self.db_credentials = aws.secretsmanager.Secret(
            f"{name}-db-credentials",
            name=namer.secret_name("db-credentials-v3"),
            description="RDS PostgreSQL credentials",
            recovery_window_in_days=0,  # Immediate deletion (dev only)
            tags=create_tags(environment, f"{name}-db-credentials"),
            opts=child_opts,
        )

        # Generate random password for database
        db_password = aws.secretsmanager.SecretVersion(
            f"{name}-db-credentials-version",
            secret_id=self.db_credentials.id,
            secret_string=json.dumps({
                "username": "postgres",
                "password": "PLACEHOLDER_SET_VIA_CLI",
                "engine": "postgres",
                "port": 5432,
            }),
            opts=child_opts,
        )

        self.register_outputs({
            "google_api_key_arn": self.google_api_key.arn,
            "anthropic_api_key_arn": self.anthropic_api_key.arn,
            "db_credentials_arn": self.db_credentials.arn,
        })
