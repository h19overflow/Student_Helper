"""
CloudFront CDN component for frontend distribution.

Creates:
- CloudFront distribution with S3 origin
- Origin Access Identity for secure S3 access
- Cache behaviors for static assets
"""

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags


class CloudFrontComponent(pulumi.ComponentResource):
    """
    CloudFront distribution for frontend static assets.

    Uses Origin Access Identity to securely serve content from S3.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        frontend_bucket_name: pulumi.Input[str],
        frontend_bucket_arn: pulumi.Input[str],
        frontend_bucket_domain: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:edge:CloudFront", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # Origin Access Identity
        self.oai = aws.cloudfront.OriginAccessIdentity(
            f"{name}-oai",
            comment=f"OAI for {name} frontend",
            opts=child_opts,
        )

        # CloudFront Distribution
        self.distribution = aws.cloudfront.Distribution(
            f"{name}-distribution",
            enabled=True,
            is_ipv6_enabled=True,
            default_root_object="index.html",
            price_class="PriceClass_100",  # US, Canada, Europe only
            origins=[
                aws.cloudfront.DistributionOriginArgs(
                    domain_name=frontend_bucket_domain,
                    origin_id="s3-frontend",
                    s3_origin_config=aws.cloudfront.DistributionOriginS3OriginConfigArgs(
                        origin_access_identity=self.oai.cloudfront_access_identity_path,
                    ),
                ),
            ],
            default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
                target_origin_id="s3-frontend",
                viewer_protocol_policy="redirect-to-https",
                allowed_methods=["GET", "HEAD", "OPTIONS"],
                cached_methods=["GET", "HEAD"],
                forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
                    query_string=False,
                    cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                        forward="none",
                    ),
                ),
                min_ttl=0,
                default_ttl=86400,
                max_ttl=31536000,
                compress=True,
            ),
            # SPA routing - return index.html for 404s
            custom_error_responses=[
                aws.cloudfront.DistributionCustomErrorResponseArgs(
                    error_code=404,
                    response_code=200,
                    response_page_path="/index.html",
                ),
                aws.cloudfront.DistributionCustomErrorResponseArgs(
                    error_code=403,
                    response_code=200,
                    response_page_path="/index.html",
                ),
            ],
            restrictions=aws.cloudfront.DistributionRestrictionsArgs(
                geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                    restriction_type="none",
                ),
            ),
            viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
                cloudfront_default_certificate=True,
            ),
            tags=create_tags(environment, f"{name}-distribution"),
            opts=child_opts,
        )

        # S3 bucket policy for CloudFront access
        self.bucket_policy = aws.s3.BucketPolicy(
            f"{name}-bucket-policy",
            bucket=frontend_bucket_name,
            policy=pulumi.Output.all(
                frontend_bucket_arn,
                self.oai.iam_arn,
            ).apply(lambda args: f"""{{
                "Version": "2012-10-17",
                "Statement": [{{
                    "Effect": "Allow",
                    "Principal": {{"AWS": "{args[1]}"}},
                    "Action": "s3:GetObject",
                    "Resource": "{args[0]}/*"
                }}]
            }}"""),
            opts=pulumi.ResourceOptions(parent=self, depends_on=[self.distribution]),
        )

        self.register_outputs({
            "distribution_id": self.distribution.id,
            "distribution_domain": self.distribution.domain_name,
        })
