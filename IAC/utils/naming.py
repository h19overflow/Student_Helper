"""
Resource naming conventions for consistent AWS resource names.

Follows pattern: {project}-{environment}-{resource}
"""

from dataclasses import dataclass


@dataclass
class ResourceNamer:
    """
    Generates consistent resource names for AWS resources.

    Attributes:
        project: Project identifier
        environment: Deployment environment (dev, staging, prod)
    """
    project: str
    environment: str

    def name(self, resource: str) -> str:
        """
        Generate a resource name.

        Args:
            resource: Resource identifier (e.g., 'vpc', 'backend-sg')

        Returns:
            Formatted resource name
        """
        return f"{self.project}-{self.environment}-{resource}"

    def bucket_name(self, suffix: str) -> str:
        """
        Generate an S3 bucket name (must be globally unique).

        Args:
            suffix: Bucket suffix (e.g., 'documents', 'vectors')

        Returns:
            Globally unique bucket name
        """
        return f"{self.project}-{self.environment}-{suffix}"

    def secret_name(self, name: str) -> str:
        """
        Generate a Secrets Manager secret name.

        Args:
            name: Secret identifier

        Returns:
            Secret name with environment prefix
        """
        return f"{self.project}/{self.environment}/{name}"
