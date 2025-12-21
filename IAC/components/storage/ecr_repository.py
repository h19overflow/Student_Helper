"""
ECR Repository Component for Lambda Container Images.

Stores Docker images for Lambda document processing pipeline (up to 10GB each).

Integration Flow:
  1. Developer builds Docker image locally: docker build -t student-helper-lambda-processor:latest .
  2. Developer authenticates with ECR: aws ecr get-login-password | docker login
  3. Developer pushes image: docker push <ECR_URL>:latest
  4. Pulumi reads image_uri from ECR repository: ecr.get_outputs().repository_url
  5. Pulumi passes to Lambda: ecr_image_uri parameter
  6. Lambda pulls image on deployment: aws lambda create-function --image-uri <ECR_URL>:latest

Access Control - Who Can Pull:
1. Lambda Service → Granted via Repository Policy (ecr:BatchGetImage, ecr:GetDownloadUrlForLayer) ✅
2. EC2 (if needed) → Via IAM Role + ECR VPC Endpoints (ecr.api, ecr.dkr) ✅
3. Developers (via AWS credentials) → IAM permissions ✅
4. Public Internet → DENIED ❌ (Private repository)

Key Features:
- scan_on_push=True: Every image is scanned for CVEs (vulnerabilities) on upload.
- Lifecycle Policy: Auto-delete old images, keep only the last 5 (saves storage costs).
- Encryption: Images encrypted at rest (AES256).
- Tag mutability: MUTABLE (allows overwriting 'latest' tag on each push).

Outputs (Pass to LambdaProcessorComponent):
  - repository_url: <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/<REPO>
  - repository_arn: arn:aws:ecr:<REGION>:<ACCOUNT>:repository/<REPO>
  - repository_name: student-helper-lambda-processor

Builder Scripts:
  - PowerShell: backend/scripts/build-lambda-image.ps1 (builds and optionally pushes)
  - Python: python -m backend.scripts.ecr_builder (build/push/build-and-push)
  - Manual: See LAMBDA_DEPLOYMENT_GUIDE.md

Example Pulumi Usage:
  ecr = EcrRepositoryComponent(name="student-helper", environment=environment)

  lambda_processor = LambdaProcessorComponent(
      ecr_image_uri=ecr.get_outputs().repository_url + ":latest",
      ...
  )
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
