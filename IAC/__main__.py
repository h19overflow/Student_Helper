"""
Pulumi program entry point for Student Helper infrastructure.

Instantiates all component resources in dependency order:
1. Configuration
2. VPC → Security Groups → IAM Roles
3. Secrets Manager, S3 Buckets, SQS Queues
4. VPC Endpoints, RDS
5. EC2 Backend, Lambda Processor
6. CloudFront, API Gateway
"""

import pulumi
import pulumi_aws as aws

from IAC.configs.environment import get_config
from IAC.utils.naming import ResourceNamer
from IAC.utils.outputs import write_outputs_to_env

# Networking
from IAC.components.networking.vpc import VpcComponent
from IAC.components.networking.security_groups import SecurityGroupsComponent
from IAC.components.networking.vpc_endpoints import VpcEndpointsComponent

# Security
from IAC.components.security.iam_roles import IamRolesComponent
from IAC.components.security.secrets_manager import SecretsManagerComponent

# Storage
from IAC.components.storage.s3_buckets import S3BucketsComponent
from IAC.components.storage.rds_postgres import RdsPostgresComponent
from IAC.components.storage.ecr_repository import EcrRepositoryComponent

# Messaging
from IAC.components.messaging.sqs_queues import SqsQueuesComponent

# Compute
from IAC.components.compute.ec2_backend import Ec2BackendComponent
from IAC.components.compute.lambda_processor import LambdaProcessorComponent
from IAC.components.compute.alb import AlbComponent

# Edge
from IAC.components.edge.cloudfront import CloudFrontComponent
from IAC.components.edge.api_gateway import ApiGatewayComponent


def _deploy_storage_only(config, namer, base_name: str) -> None:
    """Deploy only S3 buckets for development and testing (presigned URLs, etc).

    Args:
        config: Configuration object from get_config()
        namer: ResourceNamer instance
        base_name: Base name for resources
    """
    # --- S3 Buckets Only ---
    # Create empty SQS for storage-only deployment (no Lambda)
    sqs_queues = SqsQueuesComponent(
        name=base_name,
        environment=config.environment,
        namer=namer,
    )
    sqs_outputs = sqs_queues.get_outputs()

    s3_buckets = S3BucketsComponent(
        name=base_name,
        environment=config.environment,
        namer=namer,
        sqs_queue_arn=sqs_outputs.queue_arn,
    )
    s3_outputs = s3_buckets.get_outputs()

    # --- S3-only Exports ---
    storage_outputs = {
        "documents_bucket": s3_outputs.documents_bucket_name,
        "vectors_bucket": s3_outputs.vectors_bucket_name,
        "vectors_index": s3_outputs.vectors_index_name,
        "frontend_bucket": s3_outputs.frontend_bucket_name,
    }

    # Write outputs to .env file for local development
    write_outputs_to_env(storage_outputs, "infrastructure.env")

    # Export to Pulumi stack
    for key, value in storage_outputs.items():
        pulumi.export(key, value)

    pulumi.log.info("✓ S3-only deployment complete")


def main() -> None:
    """Deploy Student Helper infrastructure."""
    # Load configuration
    config = get_config()
    namer = ResourceNamer(project="student-helper", environment=config.environment)
    base_name = namer.name("")

    # Get AWS region from provider
    aws_region = aws.get_region().name

    # Check if deploying storage only
    pulumi_config = pulumi.Config()
    storage_only = pulumi_config.get_bool("storage_only") or False

    if storage_only:
        _deploy_storage_only(config, namer, base_name)
        return

    # --- Layer 1: Networking Foundation ---
    vpc = VpcComponent(
        name=base_name,
        environment=config.environment,
    )
    vpc_outputs = vpc.get_outputs()

    security_groups = SecurityGroupsComponent(
        name=base_name,
        environment=config.environment,
        vpc_id=vpc_outputs.vpc_id,
    )
    sg_outputs = security_groups.get_outputs()

    # --- Layer 2: IAM Roles ---
    iam_roles = IamRolesComponent(
        name=base_name,
        environment=config.environment,
    )
    iam_outputs = iam_roles.get_outputs()

    # --- Layer 3: Secrets, Storage, Messaging ---
    secrets = SecretsManagerComponent(
        name=base_name,
        environment=config.environment,
        namer=namer,
    )

    sqs_queues = SqsQueuesComponent(
        name=base_name,
        environment=config.environment,
        namer=namer,
    )
    sqs_outputs = sqs_queues.get_outputs()

    s3_buckets = S3BucketsComponent(
        name=base_name,
        environment=config.environment,
        namer=namer,
        sqs_queue_arn=sqs_outputs.queue_arn,
    )
    s3_outputs = s3_buckets.get_outputs()

    ecr_repository = EcrRepositoryComponent(
        name=base_name,
        environment=config.environment,
    )
    ecr_outputs = ecr_repository.get_outputs()

    # --- Layer 4: VPC Endpoints, RDS ---
    vpc_endpoints = VpcEndpointsComponent(
        name=base_name,
        environment=config.environment,
        vpc_id=vpc_outputs.vpc_id,
        subnet_ids=[vpc_outputs.private_subnet_id, vpc_outputs.lambda_subnet_id],
        security_group_id=sg_outputs.endpoints_sg_id,
        route_table_ids=[vpc_outputs.private_route_table_id],
    )

    rds = RdsPostgresComponent(
        name=base_name,
        environment=config.environment,
        config=config,
        subnet_ids=[vpc_outputs.data_subnet_id, vpc_outputs.data_subnet_id_b],
        security_group_id=sg_outputs.database_sg_id,
    )
    rds_outputs = rds.get_outputs()

    # --- Layer 5: Compute ---
    ec2_backend = Ec2BackendComponent(
        name=namer.name("backend"),
        environment=config.environment,
        config=config,
        subnet_id=vpc_outputs.private_subnet_id,
        security_group_id=sg_outputs.backend_sg_id,
        instance_profile_name=iam_roles.ec2_instance_profile.name,
    )
    ec2_outputs = ec2_backend.get_outputs()

    # ALB for EC2 backend (internal, accessed via API Gateway VPC Link)
    alb = AlbComponent(
        name=namer.name("backend"),
        environment=config.environment,
        vpc_id=vpc_outputs.vpc_id,
        subnet_ids=[vpc_outputs.private_subnet_id, vpc_outputs.lambda_subnet_id],
        security_group_id=sg_outputs.alb_sg_id,
    )
    alb_outputs = alb.get_outputs()

    alb_outputs = alb.get_outputs()

    # Register EC2 with ALB target group (HTTP API)
    alb_target_group_attachment = aws.lb.TargetGroupAttachment(
        f"{base_name}-alb-tg-attachment",
        target_group_arn=alb_outputs.target_group_arn,
        target_id=ec2_outputs.instance_id,
        port=8000,
    )

    # Construct database URL for Lambda
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    # Password will be retrieved from Secrets Manager at runtime by Lambda
    database_url = pulumi.concat(
        "postgresql+asyncpg://postgres:placeholder@",
        rds_outputs.endpoint,
        ":",
        rds_outputs.port.apply(str),
        "/",
        rds_outputs.database_name,
    )

    lambda_processor = LambdaProcessorComponent(
        name=namer.name("doc-processor"),
        environment=config.environment,
        config=config,
        role_arn=iam_outputs.lambda_role_arn,
        subnet_ids=[vpc_outputs.lambda_subnet_id],
        security_group_id=sg_outputs.lambda_sg_id,
        sqs_queue_arn=sqs_outputs.queue_arn,
        documents_bucket_name=s3_outputs.documents_bucket_name,
        vectors_bucket_name=s3_outputs.vectors_bucket_name,
        secrets_arn=secrets.google_api_key.arn,
        ecr_image_uri=pulumi.concat(ecr_outputs.repository_url, ":latest"),
        database_url=database_url,
        aws_region=aws_region,
    )
    lambda_outputs = lambda_processor.get_outputs()

    # --- Layer 6: Edge Services ---
    # API Gateway first (CloudFront depends on its endpoint)
    api_gateway = ApiGatewayComponent(
        name=base_name,
        environment=config.environment,
        vpc_id=vpc_outputs.vpc_id,
        subnet_ids=[vpc_outputs.private_subnet_id, vpc_outputs.lambda_subnet_id],
        security_group_id=sg_outputs.alb_sg_id,
        alb_listener_arn=alb_outputs.listener_arn,
    )
    api_outputs = api_gateway.get_outputs()

    # CloudFront routes to API Gateway (which routes to internal ALB via VPC Link)
    cloudfront = CloudFrontComponent(
        name=base_name,
        environment=config.environment,
        frontend_bucket_name=s3_outputs.frontend_bucket_name,
        frontend_bucket_arn=s3_outputs.frontend_bucket_arn,
        frontend_bucket_domain=s3_outputs.frontend_website_endpoint,
        api_gateway_endpoint=api_outputs.api_endpoint,
    )

    # --- Exports ---
    outputs = {
        "vpc_id": vpc_outputs.vpc_id,
        "ec2_instance_id": ec2_outputs.instance_id,
        "ec2_private_ip": ec2_outputs.private_ip,
        "alb_dns_name": alb_outputs.alb_dns_name,
        "lambda_function_name": lambda_outputs.function_name,
        "lambda_ecr_repository": ecr_outputs.repository_url,
        "rds_endpoint": rds_outputs.endpoint,
        "documents_bucket": s3_outputs.documents_bucket_name,
        "vectors_bucket": s3_outputs.vectors_bucket_name,
        "vectors_index": s3_outputs.vectors_index_name,
        "frontend_bucket": s3_outputs.frontend_bucket_name,
        "sqs_queue_url": sqs_outputs.queue_url,
        "api_endpoint": api_outputs.api_endpoint,
        "cloudfront_domain": cloudfront.distribution.domain_name,
    }

    # Write outputs to .env file for local development
    write_outputs_to_env(outputs, "infrastructure.env")

    # Export to Pulumi stack
    for key, value in outputs.items():
        pulumi.export(key, value)


# Execute
main()
