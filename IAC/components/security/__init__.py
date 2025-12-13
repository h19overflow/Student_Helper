"""
Security components for IAM and secrets management.

Components:
- IamRolesComponent: IAM roles for EC2 and Lambda
- SecretsManagerComponent: Secrets for API keys and database credentials
"""

from IAC.components.security.iam_roles import IamRolesComponent, IamRoleOutputs
from IAC.components.security.secrets_manager import SecretsManagerComponent

__all__ = [
    "IamRolesComponent",
    "IamRoleOutputs",
    "SecretsManagerComponent",
]
