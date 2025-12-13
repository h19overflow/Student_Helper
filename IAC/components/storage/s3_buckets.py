"""
S3 buckets component for object storage.

Creates:
- Documents bucket: Uploaded PDFs with versioning
- Vectors bucket: Vector embeddings storage
- Frontend bucket: Static website assets
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws
import pulumi_aws_native 
from IAC.utils.tags import create_tags
from IAC.utils.naming import ResourceNamer


@dataclass
class S3BucketOutputs:
    """Output values from S3 buckets component."""
    documents_bucket_name: pulumi.Output[str]
    documents_bucket_arn: pulumi.Output[str]
    vectors_bucket_name: pulumi.Output[str]
    vectors_bucket_arn: pulumi.Output[str]
    frontend_bucket_name: pulumi.Output[str]
    frontend_bucket_arn: pulumi.Output[str]
    frontend_website_endpoint: pulumi.Output[str]


class S3BucketsComponent(pulumi.ComponentResource):
    """
    S3 buckets for documents, vectors, and frontend assets.

    Documents bucket has versioning enabled for data protection.
    Frontend bucket is configured for static website hosting.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        namer: ResourceNamer,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:storage:S3Buckets", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # Documents bucket (uploaded PDFs)
        self.documents_bucket = aws.s3.BucketV2(
            f"{name}-documents",
            bucket=namer.bucket_name("documents"),
            tags=create_tags(environment, f"{name}-documents"),
            opts=child_opts,
        )

        aws.s3.BucketVersioningV2(
            f"{name}-documents-versioning",
            bucket=self.documents_bucket.id,
            versioning_configuration=aws.s3.BucketVersioningV2VersioningConfigurationArgs(
                status="Enabled",
            ),
            opts=child_opts,
        )

        aws.s3.BucketServerSideEncryptionConfigurationV2(
            f"{name}-documents-encryption",
            bucket=self.documents_bucket.id,
            rules=[aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="AES256",
                ),
            )],
            opts=child_opts,
        )
        # TODO: Wrong , this should be an S3vectors bucket not a regular s3 bucket.
        # Vectors bucket (embeddings)
        self.vectors_bucket = aws.s3.BucketV2(
            f"{name}-vectors",
            bucket=namer.bucket_name("vectors"),
            tags=create_tags(environment, f"{name}-vectors"),
            opts=child_opts,
        )

        aws.s3.BucketServerSideEncryptionConfigurationV2(
            f"{name}-vectors-encryption",
            bucket=self.vectors_bucket.id,
            rules=[aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="AES256",
                ),
            )],
            opts=child_opts,
        )

        # Frontend bucket (static assets)
        self.frontend_bucket = aws.s3.BucketV2(
            f"{name}-frontend",
            bucket=namer.bucket_name("frontend"),
            tags=create_tags(environment, f"{name}-frontend"),
            opts=child_opts,
        )

        aws.s3.BucketWebsiteConfigurationV2(
            f"{name}-frontend-website",
            bucket=self.frontend_bucket.id,
            index_document=aws.s3.BucketWebsiteConfigurationV2IndexDocumentArgs(
                suffix="index.html",
            ),
            error_document=aws.s3.BucketWebsiteConfigurationV2ErrorDocumentArgs(
                key="index.html",  # SPA routing
            ),
            opts=child_opts,
        )

        # Block public access on documents and vectors buckets
        for bucket_name, bucket in [
            ("documents", self.documents_bucket),
            ("vectors", self.vectors_bucket),
        ]:
            aws.s3.BucketPublicAccessBlock(
                f"{name}-{bucket_name}-public-block",
                bucket=bucket.id,
                block_public_acls=True,
                block_public_policy=True,
                ignore_public_acls=True,
                restrict_public_buckets=True,
                opts=child_opts,
            )

        self.register_outputs({
            "documents_bucket_name": self.documents_bucket.bucket,
            "documents_bucket_arn": self.documents_bucket.arn,
            "vectors_bucket_name": self.vectors_bucket.bucket,
            "vectors_bucket_arn": self.vectors_bucket.arn,
            "frontend_bucket_name": self.frontend_bucket.bucket,
            "frontend_bucket_arn": self.frontend_bucket.arn,
        })

    def get_outputs(self) -> S3BucketOutputs:
        """Get S3 bucket output values."""
        return S3BucketOutputs(
            documents_bucket_name=self.documents_bucket.bucket,
            documents_bucket_arn=self.documents_bucket.arn,
            vectors_bucket_name=self.vectors_bucket.bucket,
            vectors_bucket_arn=self.vectors_bucket.arn,
            frontend_bucket_name=self.frontend_bucket.bucket,
            frontend_bucket_arn=self.frontend_bucket.arn,
            frontend_website_endpoint=self.frontend_bucket.bucket_regional_domain_name,
        )
