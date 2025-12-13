"""
VPC endpoints component for private AWS service access.

Creates:
- S3 Gateway endpoint (free, no NAT needed for S3)
- SQS Interface endpoint (PrivateLink)
- Secrets Manager Interface endpoint (PrivateLink)
"""

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags


class VpcEndpointsComponent(pulumi.ComponentResource):
    """
    VPC endpoints for private AWS service access.

    Gateway endpoints (S3) are free and route through the VPC route table.
    Interface endpoints (SQS, Secrets Manager) use PrivateLink ENIs.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        vpc_id: pulumi.Input[str],
        subnet_ids: list[pulumi.Input[str]],
        security_group_id: pulumi.Input[str],
        route_table_ids: list[pulumi.Input[str]] | None = None,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:networking:VpcEndpoints", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)
        region = aws.get_region()

        # S3 Gateway Endpoint (free)
        self.s3_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-s3-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.name}.s3",
            vpc_endpoint_type="Gateway",
            route_table_ids=route_table_ids,
            tags=create_tags(environment, f"{name}-s3-endpoint"),
            opts=child_opts,
        )

        # SQS Interface Endpoint
        self.sqs_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-sqs-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.name}.sqs",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-sqs-endpoint"),
            opts=child_opts,
        )

        # Secrets Manager Interface Endpoint
        self.secrets_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-secrets-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.name}.secretsmanager",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-secrets-endpoint"),
            opts=child_opts,
        )

        self.register_outputs({
            "s3_endpoint_id": self.s3_endpoint.id,
            "sqs_endpoint_id": self.sqs_endpoint.id,
            "secrets_endpoint_id": self.secrets_endpoint.id,
        })
