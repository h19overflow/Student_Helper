"""
VPC Endpoints Component for Private AWS Service Access.

Concepts & Architecture:
1. The Problem: Private subnets have NO internet access. How do they reach AWS services (S3, SQS, Bedrock)?
   - Solution: VPC Endpoints.

2. Types of Endpoints Used:
   A. Gateway Endpoints (The "Portal"):
      - Used for: S3 (and DynamoDB).
      - Mechanism: Modifies the Route Table directly (routes traffic to S3).
      - Cost: FREE.
      - Location: Resides "outside" the subnet at the routing layer.

   B. Interface Endpoints (The "Tunnel"):
      - Used for: SQS, Bedrock, SSM, ECR, Secrets Manager.
      - Mechanism: Creates a Network Interface (ENI) with a private IP (e.g., 10.0.1.99) INSIDE your subnet.
      - DNS Magic: "private_dns_enabled=True" hijacks the standard AWS DNS to point to this local private IP.
      - Cost: Paid (hourly + data processing).
      - Security: protected by Security Groups (unlike Gateway endpoints).

3. Why these specific endpoints?
   - S3/SQS/Secrets/Bedrock: Core application dependencies.
   - SSM/SSMMessages/EC2Messages: Enables "Session Manager" (secure shell access) without opening Port 22 or using Bastion hosts.
   - ECR (API/DKR): Allows private EC2 instances to pull Docker images without public internet access.
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
            service_name=f"com.amazonaws.{region.id}.s3",
            vpc_endpoint_type="Gateway",
            route_table_ids=route_table_ids,
            tags=create_tags(environment, f"{name}-s3-endpoint"),
            opts=child_opts,
        )

        # SQS Interface Endpoint
        self.sqs_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-sqs-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.id}.sqs",
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
            service_name=f"com.amazonaws.{region.id}.secretsmanager",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-secrets-endpoint"),
            opts=child_opts,
        )

        # Bedrock Runtime Interface Endpoint
        self.bedrock_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-bedrock-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.id}.bedrock-runtime",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-bedrock-endpoint"),
            opts=child_opts,
        )

        # SSM Interface Endpoints (required for Session Manager)
        self.ssm_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-ssm-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.id}.ssm",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-ssm-endpoint"),
            opts=child_opts,
        )

        self.ssmmessages_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-ssmmessages-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.id}.ssmmessages",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-ssmmessages-endpoint"),
            opts=child_opts,
        )

        self.ec2messages_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-ec2messages-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.id}.ec2messages",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-ec2messages-endpoint"),
            opts=child_opts,
        )

        # ECR Endpoints (required for Docker pull from ECR)
        self.ecr_api_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-ecr-api-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.id}.ecr.api",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-ecr-api-endpoint"),
            opts=child_opts,
        )

        self.ecr_dkr_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-ecr-dkr-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.id}.ecr.dkr",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-ecr-dkr-endpoint"),
            opts=child_opts,
        )

        # S3 Vectors Interface Endpoint (required for VectorBucket access)
        self.s3_vectors_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-s3-vectors-endpoint",
            vpc_id=vpc_id,
            service_name=f"com.amazonaws.{region.id}.s3vectors",
            vpc_endpoint_type="Interface",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            private_dns_enabled=True,
            tags=create_tags(environment, f"{name}-s3-vectors-endpoint"),
            opts=child_opts,
        )

        self.register_outputs({
            "s3_endpoint_id": self.s3_endpoint.id,
            "sqs_endpoint_id": self.sqs_endpoint.id,
            "secrets_endpoint_id": self.secrets_endpoint.id,
            "bedrock_endpoint_id": self.bedrock_endpoint.id,
            "ssm_endpoint_id": self.ssm_endpoint.id,
            "ssmmessages_endpoint_id": self.ssmmessages_endpoint.id,
            "ec2messages_endpoint_id": self.ec2messages_endpoint.id,
            "ecr_api_endpoint_id": self.ecr_api_endpoint.id,
            "ecr_dkr_endpoint_id": self.ecr_dkr_endpoint.id,
            "s3_vectors_endpoint_id": self.s3_vectors_endpoint.id,
        })
