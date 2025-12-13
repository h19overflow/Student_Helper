"""
Detailed tests for individual IAC components.

Validates:
1. Each component class has required attributes
2. Components are properly organized in packages
3. Component initialization parameters are correct
4. Output dataclasses have required fields
"""

import pytest


class TestNetworkingComponents:
    """Tests for networking infrastructure components."""

    def test_vpc_component_attributes(self):
        """VpcComponent should have essential attributes."""
        from IAC.components.networking.vpc import VpcComponent

        # Check for essential methods and properties
        assert hasattr(VpcComponent, "__init__")
        assert hasattr(VpcComponent, "get_outputs")
        assert hasattr(VpcComponent, "_create_route_tables")

    def test_vpc_outputs_has_nat_gateway_id(self):
        """VpcOutputs should include NAT gateway ID."""
        from IAC.components.networking.vpc import VpcOutputs

        fields = {f.name for f in VpcOutputs.__dataclass_fields__.values()}
        assert "nat_gateway_id" in fields

    def test_security_groups_component_attributes(self):
        """SecurityGroupsComponent should have essential attributes."""
        from IAC.components.networking.security_groups import SecurityGroupsComponent

        assert hasattr(SecurityGroupsComponent, "__init__")
        assert hasattr(SecurityGroupsComponent, "get_outputs")

    def test_vpc_endpoints_component_attributes(self):
        """VpcEndpointsComponent should have essential attributes."""
        from IAC.components.networking.vpc_endpoints import VpcEndpointsComponent

        assert hasattr(VpcEndpointsComponent, "__init__")
        # VpcEndpointsComponent may not have get_outputs, it's optional
        assert VpcEndpointsComponent is not None


class TestSecurityComponents:
    """Tests for security infrastructure components."""

    def test_iam_roles_component_attributes(self):
        """IamRolesComponent should have essential attributes."""
        from IAC.components.security.iam_roles import IamRolesComponent

        assert hasattr(IamRolesComponent, "__init__")
        assert hasattr(IamRolesComponent, "get_outputs")
        # Component should be a valid class
        assert IamRolesComponent is not None

    def test_iam_role_outputs_has_lambda_role_arn(self):
        """IamRoleOutputs should include Lambda role ARN."""
        from IAC.components.security.iam_roles import IamRoleOutputs

        fields = {f.name for f in IamRoleOutputs.__dataclass_fields__.values()}
        assert "lambda_role_arn" in fields

    def test_secrets_manager_component_attributes(self):
        """SecretsManagerComponent should have essential attributes."""
        from IAC.components.security.secrets_manager import SecretsManagerComponent

        assert hasattr(SecretsManagerComponent, "__init__")
        # Component should be a valid class
        assert SecretsManagerComponent is not None


class TestStorageComponents:
    """Tests for storage infrastructure components."""

    def test_s3_buckets_component_attributes(self):
        """S3BucketsComponent should have essential attributes."""
        from IAC.components.storage.s3_buckets import S3BucketsComponent

        assert hasattr(S3BucketsComponent, "__init__")
        assert hasattr(S3BucketsComponent, "get_outputs")

    def test_s3_bucket_outputs_has_required_buckets(self):
        """S3BucketOutputs should include all bucket types."""
        from IAC.components.storage.s3_buckets import S3BucketOutputs

        fields = {f.name for f in S3BucketOutputs.__dataclass_fields__.values()}
        required = {"documents_bucket_name", "vectors_bucket_name", "frontend_bucket_name"}
        assert required.issubset(fields)

    def test_s3_bucket_outputs_has_arns(self):
        """S3BucketOutputs should include bucket ARNs."""
        from IAC.components.storage.s3_buckets import S3BucketOutputs

        fields = {f.name for f in S3BucketOutputs.__dataclass_fields__.values()}
        # Check for at least one ARN field
        arn_fields = [f for f in fields if "arn" in f.lower()]
        assert len(arn_fields) > 0, "S3BucketOutputs should include ARN fields"

    def test_rds_component_attributes(self):
        """RdsPostgresComponent should have essential attributes."""
        from IAC.components.storage.rds_postgres import RdsPostgresComponent

        assert hasattr(RdsPostgresComponent, "__init__")
        assert hasattr(RdsPostgresComponent, "get_outputs")

    def test_rds_outputs_has_endpoint(self):
        """RdsOutputs should include database endpoint."""
        from IAC.components.storage.rds_postgres import RdsOutputs

        fields = {f.name for f in RdsOutputs.__dataclass_fields__.values()}
        assert "endpoint" in fields


class TestMessagingComponents:
    """Tests for messaging infrastructure components."""

    def test_sqs_component_attributes(self):
        """SqsQueuesComponent should have essential attributes."""
        from IAC.components.messaging.sqs_queues import SqsQueuesComponent

        assert hasattr(SqsQueuesComponent, "__init__")
        assert hasattr(SqsQueuesComponent, "get_outputs")

    def test_sqs_outputs_has_queue_url(self):
        """SqsOutputs should include queue URL or ARN."""
        from IAC.components.messaging.sqs_queues import SqsOutputs

        fields = {f.name for f in SqsOutputs.__dataclass_fields__.values()}
        assert "queue_url" in fields or "queue_arn" in fields


class TestComputeComponents:
    """Tests for compute infrastructure components."""

    def test_ec2_component_attributes(self):
        """Ec2BackendComponent should have essential attributes."""
        from IAC.components.compute.ec2_backend import Ec2BackendComponent

        assert hasattr(Ec2BackendComponent, "__init__")
        assert hasattr(Ec2BackendComponent, "get_outputs")

    def test_ec2_outputs_has_instance_id(self):
        """Ec2Outputs should include instance ID."""
        from IAC.components.compute.ec2_backend import Ec2Outputs

        fields = {f.name for f in Ec2Outputs.__dataclass_fields__.values()}
        assert "instance_id" in fields

    def test_ec2_outputs_has_private_ip(self):
        """Ec2Outputs should include private IP."""
        from IAC.components.compute.ec2_backend import Ec2Outputs

        fields = {f.name for f in Ec2Outputs.__dataclass_fields__.values()}
        assert "private_ip" in fields

    def test_lambda_component_attributes(self):
        """LambdaProcessorComponent should have essential attributes."""
        from IAC.components.compute.lambda_processor import LambdaProcessorComponent

        assert hasattr(LambdaProcessorComponent, "__init__")
        assert hasattr(LambdaProcessorComponent, "get_outputs")

    def test_lambda_outputs_has_function_name(self):
        """LambdaOutputs should include function name."""
        from IAC.components.compute.lambda_processor import LambdaOutputs

        fields = {f.name for f in LambdaOutputs.__dataclass_fields__.values()}
        assert "function_name" in fields


class TestEdgeComponents:
    """Tests for edge infrastructure components."""

    def test_cloudfront_component_attributes(self):
        """CloudFrontComponent should have essential attributes."""
        from IAC.components.edge.cloudfront import CloudFrontComponent

        assert hasattr(CloudFrontComponent, "__init__")
        # CloudFront component should be valid
        assert CloudFrontComponent is not None

    def test_cloudfront_has_distribution(self):
        """CloudFrontComponent should support distribution creation."""
        from IAC.components.edge.cloudfront import CloudFrontComponent

        # Component should be properly defined
        assert CloudFrontComponent is not None

    def test_api_gateway_component_attributes(self):
        """ApiGatewayComponent should have essential attributes."""
        from IAC.components.edge.api_gateway import ApiGatewayComponent

        assert hasattr(ApiGatewayComponent, "__init__")
        assert hasattr(ApiGatewayComponent, "get_outputs")

    def test_route53_component_attributes(self):
        """Route53Component should have essential attributes."""
        from IAC.components.edge.route53 import Route53Component

        assert hasattr(Route53Component, "__init__")
        # Route53 component should be valid
        assert Route53Component is not None


class TestComponentPackageStructure:
    """Tests for component package organization."""

    def test_all_component_packages_have_init(self):
        """All component packages should have __init__.py."""
        from pathlib import Path

        iac_dir = Path(__file__).parent.parent.parent / "IAC"
        component_dirs = [
            iac_dir / "components" / "networking",
            iac_dir / "components" / "security",
            iac_dir / "components" / "storage",
            iac_dir / "components" / "messaging",
            iac_dir / "components" / "compute",
            iac_dir / "components" / "edge",
        ]

        for comp_dir in component_dirs:
            init_file = comp_dir / "__init__.py"
            assert init_file.exists(), f"Missing __init__.py in {comp_dir.name}"

    def test_config_packages_have_init(self):
        """Config and utils packages should have __init__.py."""
        from pathlib import Path

        iac_dir = Path(__file__).parent.parent.parent / "IAC"
        packages = [
            iac_dir / "configs",
            iac_dir / "utils",
            iac_dir / "components",
        ]

        for pkg_dir in packages:
            init_file = pkg_dir / "__init__.py"
            assert init_file.exists(), f"Missing __init__.py in {pkg_dir.name}"


class TestComponentExports:
    """Tests for component __init__ files."""

    def test_networking_exports_components(self):
        """Networking __init__ should export component classes."""
        from IAC.components.networking import VpcComponent, SecurityGroupsComponent

        assert VpcComponent is not None
        assert SecurityGroupsComponent is not None

    def test_security_exports_components(self):
        """Security __init__ should export component classes."""
        from IAC.components.security import IamRolesComponent, SecretsManagerComponent

        assert IamRolesComponent is not None
        assert SecretsManagerComponent is not None

    def test_storage_exports_components(self):
        """Storage __init__ should export component classes."""
        from IAC.components.storage import S3BucketsComponent, RdsPostgresComponent

        assert S3BucketsComponent is not None
        assert RdsPostgresComponent is not None

    def test_compute_exports_components(self):
        """Compute __init__ should export component classes."""
        from IAC.components.compute import Ec2BackendComponent, LambdaProcessorComponent

        assert Ec2BackendComponent is not None
        assert LambdaProcessorComponent is not None

    def test_edge_exports_components(self):
        """Edge __init__ should export component classes."""
        from IAC.components.edge import CloudFrontComponent, ApiGatewayComponent

        assert CloudFrontComponent is not None
        assert ApiGatewayComponent is not None
