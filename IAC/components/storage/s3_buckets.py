"""
S3 Buckets Component for Documents, Vectors, and Frontend Assets.

Three Buckets, Three Purposes:
1. Documents Bucket: User-uploaded PDFs.
   - Access: EC2/Lambda via IAM + S3 Gateway Endpoint (private, never public).
   - Features: Versioning (protect overwrites), Encryption (AES256), PublicAccessBlock (absolute lockdown).

2. Vectors Bucket: AI embeddings for semantic search.
   - Access: EC2/Lambda via IAM (private).
   - Features: Native vector storage, cosine similarity search, filterable metadata.

3. Frontend Bucket: Static HTML/JS/CSS for the web app.
   - Access: CloudFront ONLY via OAI (Origin Access Identity).
   - Direct S3 URL → DENIED. Must go through CDN.
   - Website config with SPA routing (error_document="index.html").

Security Principle: All buckets are PRIVATE. Access is granted via IAM Roles (for compute) or OAI (for CloudFront).
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native
from IAC.utils.tags import create_tags
from IAC.utils.naming import ResourceNamer


@dataclass
class S3BucketOutputs:
    """Output values from S3 buckets component."""
    documents_bucket_name: pulumi.Output[str]
    documents_bucket_arn: pulumi.Output[str]
    vectors_bucket_name: pulumi.Output[str]
    vectors_bucket_arn: pulumi.Output[str]
    vectors_index_name: pulumi.Output[str]
    vectors_index_arn: pulumi.Output[str]
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
        self.documents_bucket = aws.s3.Bucket(
            f"{name}-documents",
            bucket=namer.bucket_name("documents"),
            tags=create_tags(environment, f"{name}-documents"),
            opts=child_opts,
        )

        aws.s3.BucketVersioning(
            f"{name}-documents-versioning",
            bucket=self.documents_bucket.id,
            versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
                status="Enabled",
            ),
            opts=child_opts,
        )

        aws.s3.BucketServerSideEncryptionConfiguration(
            f"{name}-documents-encryption",
            bucket=self.documents_bucket.id,
            rules=[aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="AES256",
                ),
            )],
            opts=child_opts,
        )
        # S3 Vectors bucket for embeddings storage
        self.vectors_bucket = aws_native.s3vectors.VectorBucket(
            f"{name}-vectors",
            vector_bucket_name=namer.bucket_name("vectors"),
            encryption_configuration=aws_native.s3vectors.VectorBucketEncryptionConfigurationArgs(
                sse_type="AES256",
            ),
            opts=child_opts,
        )

        # Vector index for document embeddings
        # Dimension 1536 matches Amazon Titan Embeddings v2
        # text_content stored as non-filterable (large context, not for queries)
        # Filterable by default: document_id, session_id, page_number, chunk_index
        self.vectors_index = aws_native.s3vectors.Index(
            f"{name}-vectors-index",
            vector_bucket_name=self.vectors_bucket.vector_bucket_name,
            index_name="documents",
            dimension=1536,
            data_type="float32",
            distance_metric="cosine",
            metadata_configuration=aws_native.s3vectors.IndexMetadataConfigurationArgs(
                non_filterable_metadata_keys=["text_content"],
            ),
            opts=pulumi.ResourceOptions(parent=self, depends_on=[self.vectors_bucket]),
        )

        # Frontend bucket (static assets)
        self.frontend_bucket = aws.s3.Bucket(
            f"{name}-frontend",
            bucket=namer.bucket_name("frontend"),
            tags=create_tags(environment, f"{name}-frontend"),
            opts=child_opts,
        )

        aws.s3.BucketWebsiteConfiguration(
            f"{name}-frontend-website",
            bucket=self.frontend_bucket.id,
            index_document=aws.s3.BucketWebsiteConfigurationIndexDocumentArgs(
                suffix="index.html",
            ),
            error_document=aws.s3.BucketWebsiteConfigurationErrorDocumentArgs(
                key="index.html",  # SPA routing
            ),
            opts=child_opts,
        )

        # Block public access on documents bucket
        aws.s3.BucketPublicAccessBlock(
            f"{name}-documents-public-block",
            bucket=self.documents_bucket.id,
            block_public_acls=True,
            block_public_policy=True,
            ignore_public_acls=True,
            restrict_public_buckets=True,
            opts=child_opts,
        )

        self.register_outputs({
            "documents_bucket_name": self.documents_bucket.bucket,
            "documents_bucket_arn": self.documents_bucket.arn,
            "vectors_bucket_name": self.vectors_bucket.vector_bucket_name,
            "vectors_bucket_arn": self.vectors_bucket.vector_bucket_arn,
            "vectors_index_name": self.vectors_index.index_name,
            "vectors_index_arn": self.vectors_index.index_arn,
            "frontend_bucket_name": self.frontend_bucket.bucket,
            "frontend_bucket_arn": self.frontend_bucket.arn,
        })

    def get_outputs(self) -> S3BucketOutputs:
        """Get S3 bucket output values."""
        return S3BucketOutputs(
            documents_bucket_name=self.documents_bucket.bucket,
            documents_bucket_arn=self.documents_bucket.arn,
            vectors_bucket_name=self.vectors_bucket.vector_bucket_name,
            vectors_bucket_arn=self.vectors_bucket.vector_bucket_arn,
            vectors_index_name=self.vectors_index.index_name,
            vectors_index_arn=self.vectors_index.index_arn,
            frontend_bucket_name=self.frontend_bucket.bucket,
            frontend_bucket_arn=self.frontend_bucket.arn,
            frontend_website_endpoint=self.frontend_bucket.bucket_regional_domain_name,
        )
