"""
Lambda processor component for document processing.

Creates:
- Lambda function in VPC for RDS access
- SQS event source mapping for job triggers
- CloudWatch log group for function logs
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags
from IAC.configs.base import EnvironmentConfig


@dataclass
class LambdaOutputs:
    """Output values from Lambda component."""
    function_arn: pulumi.Output[str]
    function_name: pulumi.Output[str]


class LambdaProcessorComponent(pulumi.ComponentResource):
    """
    Lambda function for document processing pipeline.

    Triggered by SQS queue, processes documents through:
    parse -> chunk -> embed -> index workflow.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        config: EnvironmentConfig,
        role_arn: pulumi.Input[str],
        subnet_ids: list[pulumi.Input[str]],
        security_group_id: pulumi.Input[str],
        sqs_queue_arn: pulumi.Input[str],
        documents_bucket_name: pulumi.Input[str],
        vectors_bucket_name: pulumi.Input[str],
        secrets_arn: pulumi.Input[str],
        ecr_image_uri: pulumi.Input[str],
        database_url: pulumi.Input[str],
        aws_region: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:compute:LambdaProcessor", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # CloudWatch Log Group
        self.log_group = aws.cloudwatch.LogGroup(
            f"{name}-logs",
            name=f"/aws/lambda/{name}",
            retention_in_days=30,
            tags=create_tags(environment, f"{name}-logs"),
            opts=child_opts,
        )

        # Lambda Function (Docker image from ECR)
        self.function = aws.lambda_.Function(
            f"{name}-function",
            name=name,
            role=role_arn,
            # Use container image instead of ZIP deployment
            image_uri=ecr_image_uri,
            image_config=aws.lambda_.ImageConfigArgs(
                # Handler is embedded in Dockerfile CMD
                # but we can override if needed
                command=["backend.core.document_processing.lambda_handler.handler"],
            ),
            memory_size=config.lambda_memory,
            timeout=config.lambda_timeout,
            vpc_config=aws.lambda_.FunctionVpcConfigArgs(
                subnet_ids=subnet_ids,
                security_group_ids=[security_group_id],
            ),
            environment=aws.lambda_.FunctionEnvironmentArgs(
                variables={
                    "ENVIRONMENT": environment,
                    "DOCUMENTS_BUCKET": documents_bucket_name,
                    "VECTORS_BUCKET": vectors_bucket_name,
                    "SECRETS_ARN": secrets_arn,
                    "DATABASE_URL": database_url,
                    "AWS_REGION": aws_region,
                    "LOG_LEVEL": "INFO",
                },
            ),
            package_type="Image",  # Specify container image type
            tags=create_tags(environment, f"{name}-function"),
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[self.log_group],
            ),
        )

        # SQS Event Source Mapping
        self.event_source = aws.lambda_.EventSourceMapping(
            f"{name}-sqs-trigger",
            event_source_arn=sqs_queue_arn,
            function_name=self.function.arn,
            batch_size=1,  # Process one document at a time
            maximum_batching_window_in_seconds=0,
            opts=child_opts,
        )

        self.register_outputs({
            "function_arn": self.function.arn,
            "function_name": self.function.name,
        })

    def get_outputs(self) -> LambdaOutputs:
        """Get Lambda output values."""
        return LambdaOutputs(
            function_arn=self.function.arn,
            function_name=self.function.name,
        )
