"""
Base configuration dataclass for environment settings.

Provides type-safe configuration structure loaded from Pulumi stack configs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentConfig:
    """
    Environment-specific configuration for infrastructure deployment.

    Attributes:
        environment: Deployment environment (dev, staging, prod)
        domain: Base domain for the application
        ec2_instance_type: EC2 instance type for backend
        rds_instance_class: RDS instance class for PostgreSQL
        rds_allocated_storage: RDS storage in GB
        lambda_memory: Lambda function memory in MB
        lambda_timeout: Lambda function timeout in seconds
        enable_deletion_protection: Enable deletion protection for databases
        multi_az: Enable multi-AZ deployment for RDS
    """
    environment: str
    domain: str
    ec2_instance_type: str
    rds_instance_class: str
    rds_allocated_storage: int
    lambda_memory: int
    lambda_timeout: int
    enable_deletion_protection: bool
    multi_az: bool

    @property
    def is_production(self) -> bool:
        """Check if this is a production environment."""
        return self.environment == "prod"

    @property
    def api_subdomain(self) -> str:
        """Get the API subdomain."""
        return f"api.{self.domain}"

    def get_tags(self) -> dict[str, str]:
        """Get environment-specific tags."""
        return {
            "Environment": self.environment,
        }
