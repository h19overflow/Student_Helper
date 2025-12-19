"""
CloudFront CDN Component for Frontend Distribution.

Architectural Strategy: "Single Domain / Unified Frontend"
1. The Problem: Connecting a Frontend (S3) and Backend (ALB) usually involves two domains, leading to CORS issues and complex configurations.
2. The Solution: Use CloudFront as the global router/proxy.
   - https://domain.com/      -> S3 (Frontend Assets)
   - https://domain.com/api/* -> ALB (Backend API)
   - https://domain.com/ws/*  -> ALB (WebSockets)

Key Components:
1. Origins (Sources of Truth):
   - S3 Origin: Stores static HTML/JS/CSS. Secured via OAI (Origin Access Identity) so users CANNOT bypass CloudFront.
   - ALB Origin: The dynamic backend server.

2. Behavior Rules (The Router):
   - /ws/*: Disables caching, enables "Origin Request Policies" to forward WebSocket headers (Upgrade, Connection).
   - /api/*: Disables caching, forwards Authorization headers.
   - Default (*): Caches static assets globally for high performance.

3. "SPA Hack" (Custom Error Responses):
   - Single Page Apps (React/Vue) handle routing in the browser.
   - If a user visits /dashboard, S3 returns 404 (file doesn't exist).
   - We catch that 404 and return index.html with a 200 OK, allowing the React Router to take over.
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
        alb_dns_name: pulumi.Input[str],
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

        # Origin Request Policy for WebSockets (Forward Host, Upgrade, Connection)
        self.ws_origin_request_policy = aws.cloudfront.OriginRequestPolicy(
            f"{name}-ws-policy",
            comment="Policy for WebSocket forwarding",
            headers_config=aws.cloudfront.OriginRequestPolicyHeadersConfigArgs(
                header_behavior="whitelist",
                headers=aws.cloudfront.OriginRequestPolicyHeadersConfigHeadersArgs(
                    items=["Host", "Sec-WebSocket-Key", "Sec-WebSocket-Version", "Sec-WebSocket-Protocol"],
                ),
            ),
            cookies_config=aws.cloudfront.OriginRequestPolicyCookiesConfigArgs(
                cookie_behavior="all",
            ),
            query_strings_config=aws.cloudfront.OriginRequestPolicyQueryStringsConfigArgs(
                query_string_behavior="all",
            ),
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
                    domain_name=alb_dns_name,
                    origin_id="alb-backend",
                    custom_origin_config=aws.cloudfront.DistributionOriginCustomOriginConfigArgs(
                        http_port=80,
                        https_port=443,
                        origin_protocol_policy="http-only",
                        origin_ssl_protocols=["TLSv1.2"],
                    ),
                ),
                aws.cloudfront.DistributionOriginArgs(
                    domain_name=frontend_bucket_domain,
                    origin_id="s3-frontend",
                    s3_origin_config=aws.cloudfront.DistributionOriginS3OriginConfigArgs(
                        origin_access_identity=self.oai.cloudfront_access_identity_path,
                    ),
                ),
            ],

            ordered_cache_behaviors=[
                # WebSocket path - forward everything to ALB
                aws.cloudfront.DistributionOrderedCacheBehaviorArgs(
                    path_pattern="/ws/*",
                    target_origin_id="alb-backend",
                    viewer_protocol_policy="redirect-to-https",
                    allowed_methods=["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                    cached_methods=["GET", "HEAD"],
                    compress=False,  # Don't compress WS streams
                    default_ttl=0,
                    min_ttl=0,
                    max_ttl=0,
                    forwarded_values=aws.cloudfront.DistributionOrderedCacheBehaviorForwardedValuesArgs(
                        query_string=True,
                        cookies=aws.cloudfront.DistributionOrderedCacheBehaviorForwardedValuesCookiesArgs(
                            forward="all",
                        ),
                        headers=["Host", "Sec-WebSocket-Key", "Sec-WebSocket-Version", "Sec-WebSocket-Protocol"],
                    ),
                ),
                # API path - forward to ALB (optional, but good for unification)
                aws.cloudfront.DistributionOrderedCacheBehaviorArgs(
                    path_pattern="/api/*",
                    target_origin_id="alb-backend",
                    viewer_protocol_policy="redirect-to-https",
                    allowed_methods=["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                    cached_methods=["GET", "HEAD"],
                    compress=True,
                    default_ttl=0,
                    min_ttl=0,
                    max_ttl=0,
                    forwarded_values=aws.cloudfront.DistributionOrderedCacheBehaviorForwardedValuesArgs(
                        query_string=True,
                        cookies=aws.cloudfront.DistributionOrderedCacheBehaviorForwardedValuesCookiesArgs(
                            forward="all",
                        ),
                        headers=["Authorization", "Host"],
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
