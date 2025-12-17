"""
Infrastructure constants for Student Helper.

Contains CIDR blocks, instance types, and default configurations.
"""

from typing import Final

# VPC Configuration
VPC_CIDR: Final[str] = "10.0.0.0/16"

# Subnet CIDR blocks
SUBNET_CIDRS: Final[dict[str, str]] = {
    "private": "10.0.1.0/24",  # EC2 Backend
    "lambda": "10.0.2.0/24",   # Lambda Processor
    "data": "10.0.3.0/24",     # RDS PostgreSQL (AZ-a)
    "data_b": "10.0.4.0/24",   # RDS PostgreSQL (AZ-b)
}

# Availability zones (ap-southeast-2)
AVAILABILITY_ZONES: Final[list[str]] = [
    "ap-southeast-2a",
    "ap-southeast-2b",
    "ap-southeast-2c",
]

# EC2 Instance types by environment
INSTANCE_TYPES: Final[dict[str, str]] = {
    "dev": "t3.micro",
    "staging": "t3.small",
    "prod": "t3.small",
}

# RDS Instance classes by environment
RDS_INSTANCE_CLASSES: Final[dict[str, str]] = {
    "dev": "db.t3.micro",
    "staging": "db.t3.small",
    "prod": "db.t3.medium",
}

# Lambda configuration
LAMBDA_DEFAULTS: Final[dict[str, int]] = {
    "memory_mb": 512,
    "timeout_seconds": 300,
    "reserved_concurrency": 10,
}

# SQS configuration
SQS_DEFAULTS: Final[dict[str, int]] = {
    "visibility_timeout_seconds": 360,  # 6 minutes (Lambda timeout + buffer)
    "message_retention_seconds": 1209600,  # 14 days
    "max_receive_count": 3,  # Retries before DLQ
}

# Default tags applied to all resources
DEFAULT_TAGS: Final[dict[str, str]] = {
    "Project": "student-helper",
    "ManagedBy": "pulumi",
}

# Port configurations
PORTS: Final[dict[str, int]] = {
    "http": 80,
    "https": 443,
    "fastapi": 8000,
    "postgres": 5432,
}

# S3 bucket name suffixes
S3_BUCKET_SUFFIXES: Final[dict[str, str]] = {
    "documents": "documents",
    "vectors": "vectors",
    "frontend": "frontend",
}
