"""
ECR repository component for Lambda container images.

Creates:
- ECR repository for Lambda processor container images
- Lifecycle policy to manage image retention
- Image scanning configuration for security
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags


@dataclass
class EcrRepositoryOutputs:
    """Output values from ECR repository component."""
    repository_url: pulumi.Output[str]
    repository_arn: pulumi.Output[str]
    repository_name: pulumi.Output[str]


class EcrRepositoryComponent(pulumi.ComponentResource):
    """
    ECR repository for Lambda processor container images.

    Stores Docker images up to 10GB for Lambda deployment.
    Enables image scanning and lifecycle management.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:storage:EcrRepository", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # ECR Repository
        self.repository = aws.ecr.Repository(
            f"{name}-lambda-repo",
            name=f"{name}-lambda-processor",
            image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
                scan_on_push=True,  # Scan images for vulnerabilities
            ),
            image_tag_mutability="MUTABLE",  # Allow tag updates
            encryption_configurations=[
                aws.ecr.RepositoryEncryptionConfigurationArgs(
                    encryption_type="AES256",  # Encrypt images at rest
                ),
            ],
            tags=create_tags(environment, f"{name}-lambda-repo"),
            opts=child_opts,
        )

        # Lifecycle Policy: Keep last 5 images, delete older ones
        aws.ecr.LifecyclePolicy(
            f"{name}-lambda-lifecycle",
            repository=self.repository.name,
            policy="""{
                "rules": [{
                    "rulePriority": 1,
                    "description": "Keep last 5 images",
                    "selection": {
                        "tagStatus": "any",
                        "countType": "imageCountMoreThan",
                        "countNumber": 5
                    },
                    "action": {
                        "type": "expire"
                    }
                }]
            }""",
            opts=child_opts,
        )

        # Repository Policy: Allow Lambda service to pull images
        aws.ecr.RepositoryPolicy(
            f"{name}-lambda-repo-policy",
            repository=self.repository.name,
            policy=pulumi.Output.json_dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "LambdaECRImageRetrievalPolicy",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": [
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer",
                        ],
                    },
                ],
            }),
            opts=child_opts,
        )

        self.register_outputs({
            "repository_url": self.repository.repository_url,
            "repository_arn": self.repository.arn,
            "repository_name": self.repository.name,
        })

    def get_outputs(self) -> EcrRepositoryOutputs:
        """Get ECR repository output values."""
        return EcrRepositoryOutputs(
            repository_url=self.repository.repository_url,
            repository_arn=self.repository.arn,
            repository_name=self.repository.name,
        )
