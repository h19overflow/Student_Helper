"""
Storage components for S3 and RDS.

Components:
- S3BucketsComponent: Documents, vectors, and frontend buckets
- RdsPostgresComponent: RDS PostgreSQL database
"""

from IAC.components.storage.s3_buckets import S3BucketsComponent, S3BucketOutputs
from IAC.components.storage.rds_postgres import RdsPostgresComponent, RdsOutputs

__all__ = [
    "S3BucketsComponent",
    "S3BucketOutputs",
    "RdsPostgresComponent",
    "RdsOutputs",
]
