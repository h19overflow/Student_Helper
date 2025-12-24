"""
ECR image builder utility for Lambda deployment.

Usage:
    python -m backend.scripts.ecr_builder build --environment dev
    python -m backend.scripts.ecr_builder push --environment dev
    python -m backend.scripts.ecr_builder build-and-push --environment prod

Purpose:
- Build Docker image locally
- Authenticate with AWS ECR
- Push image to ECR repository
- Print image URI for Pulumi configuration

Dependencies: boto3, docker
System role: CI/CD helper for Lambda Docker deployments
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class ECRBuilder:
    """Build and push Lambda Docker images to ECR."""

    def __init__(self, environment: str, skip_validation: bool = False):
        """
        Initialize builder.

        Args:
            environment: Deployment environment (dev, staging, prod)
            skip_validation: Skip AWS credential validation
        """
        self.environment = environment
        self.skip_validation = skip_validation

        # Paths - use project root as Docker build context
        self.project_root = Path(__file__).parent.parent.parent
        self.lambda_dir = self.project_root / "backend" / "core" / "document_processing"
        self.dockerfile = self.lambda_dir / "Dockerfile"

        # Image configuration
        self.image_name = "student-helper-lambda-processor"
        self.image_tag = "latest"
        self.image_local = f"{self.image_name}:{self.image_tag}"

        # Validate paths
        if not self.dockerfile.exists():
            raise FileNotFoundError(f"Dockerfile not found: {self.dockerfile}")

    def build_image(self) -> bool:
        """
        Build Docker image locally.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Building image: {self.image_local}")
            logger.info(f"Dockerfile: {self.dockerfile}")

            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "--provenance=false",
                    "--platform=linux/amd64",
                    "-t",
                    self.image_local,
                    "-f",
                    str(self.dockerfile),
                    str(self.project_root),  # Build context is project root for COPY paths
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info("✓ Image built successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Build failed: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("Docker not found. Install Docker Desktop and try again.")
            return False

    def get_ecr_repository_url(self) -> Optional[str]:
        """
        Get ECR repository URL from Pulumi stack.

        Returns:
            str: ECR repository URL or None if not found
        """
        try:
            logger.info(f"Retrieving ECR repository URL from Pulumi stack...")

            result = subprocess.run(
                [
                    "pulumi",
                    "stack",
                    "output",
                    "-s",
                    "studdy-buddy" if self.environment == "dev" else self.environment,
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=str(self.project_root / "IAC"),  # Run in IAC directory
            )

            outputs = json.loads(result.stdout)
            ecr_url = outputs.get("lambda_ecr_repository")  # Matches Pulumi export key

            if not ecr_url:
                logger.error(
                    "ECR repository URL not found in Pulumi outputs. "
                    "Ensure IAC is deployed."
                )
                return None

            logger.info(f"ECR Repository: {ecr_url}")
            return ecr_url

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to retrieve Pulumi outputs: {e.stderr}")
            return None
        except json.JSONDecodeError:
            logger.error("Failed to parse Pulumi outputs")
            return None
        except FileNotFoundError:
            logger.error("Pulumi CLI not found. Install Pulumi and try again.")
            return None

    def authenticate_with_ecr(self, ecr_url: str) -> bool:
        """
        Authenticate Docker with AWS ECR.

        Args:
            ecr_url: ECR repository URL

        Returns:
            bool: True if successful
        """
        try:
            logger.info("Authenticating with AWS ECR...")

            # Extract AWS account ID and region
            parts = ecr_url.split(".")
            aws_account_id = parts[0]
            aws_region = parts[3]

            # Get ECR login password
            result = subprocess.run(
                [
                    "aws",
                    "ecr",
                    "get-login-password",
                    "--region",
                    aws_region,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            password = result.stdout.strip()

            # Docker login
            registry = f"{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com"
            docker_login_result = subprocess.run(
                ["docker", "login", "--username", "AWS", "--password-stdin", registry],
                input=password,
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info("✓ ECR authentication successful")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Authentication failed: {e.stderr}")
            return False
        except (IndexError, ValueError):
            logger.error(f"Invalid ECR URL format: {ecr_url}")
            return False

    def push_image(self, ecr_url: str) -> str:
        """
        Push image to ECR.

        Args:
            ecr_url: ECR repository URL

        Returns:
            str: Full image URI (with tag) or empty string if failed
        """
        try:
            # Tag image for ECR
            ecr_image_tag = f"{ecr_url}:latest"
            logger.info(f"Tagging image: {ecr_image_tag}")

            subprocess.run(
                ["docker", "tag", self.image_local, ecr_image_tag],
                check=True,
                capture_output=True,
            )

            # Push to ECR
            logger.info("Pushing image to ECR...")
            subprocess.run(
                ["docker", "push", ecr_image_tag],
                check=True,
                capture_output=True,
            )

            logger.info(f"✓ Image pushed successfully")
            logger.info(f"Image URI: {ecr_image_tag}")
            return ecr_image_tag

        except subprocess.CalledProcessError as e:
            logger.error(f"Push failed: {e.stderr}")
            return ""

    def build_and_push(self) -> Optional[str]:
        """
        Build and push image in one operation.

        Returns:
            str: Full image URI or None if failed
        """
        # Build locally
        if not self.build_image():
            return None

        # Get ECR URL
        ecr_url = self.get_ecr_repository_url()
        if not ecr_url:
            return None

        # Authenticate
        if not self.authenticate_with_ecr(ecr_url):
            return None

        # Push
        image_uri = self.push_image(ecr_url)
        return image_uri if image_uri else None


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m backend.scripts.ecr_builder COMMAND --environment ENV")
        print("Commands: build, push, build-and-push")
        sys.exit(1)

    command = sys.argv[1]
    environment = None

    # Parse --environment flag
    if "--environment" in sys.argv:
        idx = sys.argv.index("--environment")
        if idx + 1 < len(sys.argv):
            environment = sys.argv[idx + 1]

    if not environment:
        logger.error("--environment flag is required")
        sys.exit(1)

    try:
        builder = ECRBuilder(environment)

        if command == "build":
            success = builder.build_image()
            sys.exit(0 if success else 1)

        elif command == "push":
            ecr_url = builder.get_ecr_repository_url()
            if not ecr_url:
                sys.exit(1)

            if not builder.authenticate_with_ecr(ecr_url):
                sys.exit(1)

            result = builder.push_image(ecr_url)
            sys.exit(0 if result else 1)

        elif command == "build-and-push":
            result = builder.build_and_push()
            sys.exit(0 if result else 1)

        else:
            logger.error(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
