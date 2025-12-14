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

from IAC.configs.environment import get_config
from IAC.utils.naming import ResourceNamer

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

# Edge
from IAC.components.edge.cloudfront import CloudFrontComponent
from IAC.components.edge.api_gateway import ApiGatewayComponent


def main() -> None:
    """Deploy Student Helper infrastructure."""
    # Load configuration
    config = get_config()
    namer = ResourceNamer(project="student-helper", environment=config.environment)
    base_name = namer.name("")

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

    s3_buckets = S3BucketsComponent(
        name=base_name,
        environment=config.environment,
        namer=namer,
    )
    s3_outputs = s3_buckets.get_outputs()

    ecr_repository = EcrRepositoryComponent(
        name=base_name,
        environment=config.environment,
    )
    ecr_outputs = ecr_repository.get_outputs()

    sqs_queues = SqsQueuesComponent(
        name=base_name,
        environment=config.environment,
        namer=namer,
    )
    sqs_outputs = sqs_queues.get_outputs()

    # --- Layer 4: VPC Endpoints, RDS ---
    vpc_endpoints = VpcEndpointsComponent(
        name=base_name,
        environment=config.environment,
        vpc_id=vpc_outputs.vpc_id,
        subnet_ids=[vpc_outputs.private_subnet_id, vpc_outputs.lambda_subnet_id],
        security_group_id=sg_outputs.endpoints_sg_id,
    )

    rds = RdsPostgresComponent(
        name=base_name,
        environment=config.environment,
        config=config,
        subnet_ids=[vpc_outputs.data_subnet_id],
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
    )
    lambda_outputs = lambda_processor.get_outputs()

    # --- Layer 6: Edge Services ---
    cloudfront = CloudFrontComponent(
        name=base_name,
        environment=config.environment,
        frontend_bucket_arn=s3_outputs.frontend_bucket_arn,
        frontend_bucket_domain=s3_outputs.frontend_website_endpoint,
    )

    api_gateway = ApiGatewayComponent(
        name=base_name,
        environment=config.environment,
        vpc_id=vpc_outputs.vpc_id,
        subnet_ids=[vpc_outputs.private_subnet_id],
        security_group_id=sg_outputs.backend_sg_id,
        ec2_private_ip=ec2_outputs.private_ip,
    )
    api_outputs = api_gateway.get_outputs()

    # --- Exports ---
    pulumi.export("vpc_id", vpc_outputs.vpc_id)
    pulumi.export("ec2_instance_id", ec2_outputs.instance_id)
    pulumi.export("ec2_private_ip", ec2_outputs.private_ip)
    pulumi.export("lambda_function_name", lambda_outputs.function_name)
    pulumi.export("lambda_ecr_repository", ecr_outputs.repository_url)
    pulumi.export("rds_endpoint", rds_outputs.endpoint)
    pulumi.export("documents_bucket", s3_outputs.documents_bucket_name)
    pulumi.export("vectors_bucket", s3_outputs.vectors_bucket_name)
    pulumi.export("vectors_index", s3_outputs.vectors_index_name)
    pulumi.export("frontend_bucket", s3_outputs.frontend_bucket_name)
    pulumi.export("sqs_queue_url", sqs_outputs.queue_url)
    pulumi.export("api_endpoint", api_outputs.api_endpoint)
    pulumi.export("cloudfront_domain", cloudfront.distribution.domain_name)


# Execute
main()
