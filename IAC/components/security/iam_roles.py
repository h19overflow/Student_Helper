"""
IAM roles component for compute resources.

Creates:
- EC2 instance role with S3, SQS, Secrets Manager access
- Lambda execution role with VPC, S3, Secrets Manager access
"""

import json
from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags


@dataclass
class IamRoleOutputs:
    """Output values from IAM roles component."""
    ec2_role_arn: pulumi.Output[str]
    ec2_instance_profile_arn: pulumi.Output[str]
    lambda_role_arn: pulumi.Output[str]


class IamRolesComponent(pulumi.ComponentResource):
    """
    IAM roles for EC2 and Lambda compute resources.

    Follows least-privilege principle with specific resource permissions.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:security:IamRoles", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # EC2 assume role policy
        ec2_assume_policy = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }],
        })

        # Lambda assume role policy
        lambda_assume_policy = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }],
        })

        # EC2 Role
        self.ec2_role = aws.iam.Role(
            f"{name}-ec2-role",
            assume_role_policy=ec2_assume_policy,
            tags=create_tags(environment, f"{name}-ec2-role"),
            opts=child_opts,
        )

        # EC2 Instance Profile
        self.ec2_instance_profile = aws.iam.InstanceProfile(
            f"{name}-ec2-profile",
            role=self.ec2_role.name,
            tags=create_tags(environment, f"{name}-ec2-profile"),
            opts=child_opts,
        )

        # EC2 Policy - S3, SQS, Secrets Manager, CloudWatch
        ec2_policy = aws.iam.RolePolicy(
            f"{name}-ec2-policy",
            role=self.ec2_role.id,
            policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:ListBucket",
                            "s3:DeleteObject",
                        ],
                        "Resource": ["arn:aws:s3:::*"],
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "sqs:SendMessage",
                            "sqs:ReceiveMessage",
                            "sqs:DeleteMessage",
                            "sqs:GetQueueAttributes",
                        ],
                        "Resource": ["arn:aws:sqs:*:*:*"],
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "secretsmanager:GetSecretValue",
                        ],
                        "Resource": ["arn:aws:secretsmanager:*:*:secret:*"],
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        "Resource": ["arn:aws:logs:*:*:*"],
                    },
                ],
            }),
            opts=child_opts,
        )

        # Lambda Role
        self.lambda_role = aws.iam.Role(
            f"{name}-lambda-role",
            assume_role_policy=lambda_assume_policy,
            tags=create_tags(environment, f"{name}-lambda-role"),
            opts=child_opts,
        )

        # Attach AWS managed policies for Lambda
        aws.iam.RolePolicyAttachment(
            f"{name}-lambda-basic-execution",
            role=self.lambda_role.name,
            policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            opts=child_opts,
        )

        aws.iam.RolePolicyAttachment(
            f"{name}-lambda-vpc-access",
            role=self.lambda_role.name,
            policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
            opts=child_opts,
        )

        # Lambda custom policy - S3, SQS, Secrets Manager
        lambda_policy = aws.iam.RolePolicy(
            f"{name}-lambda-policy",
            role=self.lambda_role.id,
            policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:ListBucket",
                        ],
                        "Resource": ["arn:aws:s3:::*"],
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "sqs:ReceiveMessage",
                            "sqs:DeleteMessage",
                            "sqs:GetQueueAttributes",
                        ],
                        "Resource": ["arn:aws:sqs:*:*:*"],
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "secretsmanager:GetSecretValue",
                        ],
                        "Resource": ["arn:aws:secretsmanager:*:*:secret:*"],
                    },
                ],
            }),
            opts=child_opts,
        )

        self.register_outputs({
            "ec2_role_arn": self.ec2_role.arn,
            "ec2_instance_profile_arn": self.ec2_instance_profile.arn,
            "lambda_role_arn": self.lambda_role.arn,
        })

    def get_outputs(self) -> IamRoleOutputs:
        """Get IAM role output values."""
        return IamRoleOutputs(
            ec2_role_arn=self.ec2_role.arn,
            ec2_instance_profile_arn=self.ec2_instance_profile.arn,
            lambda_role_arn=self.lambda_role.arn,
        )
