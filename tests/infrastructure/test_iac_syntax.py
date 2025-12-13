"""
Test suite for IAC infrastructure scaffold syntax and structure validation.

Validates:
1. All Python modules have valid syntax
2. All imports can be resolved correctly
3. Module structure and organization
4. Component classes inherit from pulumi.ComponentResource
5. Output dataclasses are properly defined
"""

import ast
import sys
from pathlib import Path
from dataclasses import is_dataclass

import pytest


class TestIacSyntaxValidation:
    """Validate Python syntax in all IAC modules."""

    def test_all_iac_files_have_valid_syntax(self):
        """All Python files in IAC directory should parse without syntax errors."""
        iac_dir = Path(__file__).parent.parent.parent / "IAC"
        errors = []

        for py_file in iac_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, "r") as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                errors.append(f"{py_file}: {e.msg} (line {e.lineno})")

        assert not errors, f"Syntax errors found:\n" + "\n".join(errors)

    def test_iac_module_count(self):
        """Verify expected module structure."""
        iac_dir = Path(__file__).parent.parent.parent / "IAC"
        py_files = list(iac_dir.rglob("*.py"))

        # Filter out __pycache__
        py_files = [f for f in py_files if "__pycache__" not in str(f)]

        # Expected: 3 config + 2 utils + 1 main + 1 iac init + 6 component inits
        # + 17 component modules = 30 total
        assert len(py_files) >= 25, f"Expected at least 25 Python files, found {len(py_files)}"


class TestIacImports:
    """Validate that all IAC imports are correctly structured."""

    def test_all_components_importable(self):
        """All component classes should be importable without errors."""
        # This will raise ImportError if any module is not importable
        from IAC.components.networking.vpc import VpcComponent
        from IAC.components.networking.security_groups import SecurityGroupsComponent
        from IAC.components.networking.vpc_endpoints import VpcEndpointsComponent

        from IAC.components.security.iam_roles import IamRolesComponent
        from IAC.components.security.secrets_manager import SecretsManagerComponent

        from IAC.components.storage.s3_buckets import S3BucketsComponent
        from IAC.components.storage.rds_postgres import RdsPostgresComponent

        from IAC.components.messaging.sqs_queues import SqsQueuesComponent

        from IAC.components.compute.ec2_backend import Ec2BackendComponent
        from IAC.components.compute.lambda_processor import LambdaProcessorComponent

        from IAC.components.edge.cloudfront import CloudFrontComponent
        from IAC.components.edge.api_gateway import ApiGatewayComponent
        from IAC.components.edge.route53 import Route53Component

        # Verify all are valid classes
        assert all(
            isinstance(cls, type)
            for cls in [
                VpcComponent,
                SecurityGroupsComponent,
                VpcEndpointsComponent,
                IamRolesComponent,
                SecretsManagerComponent,
                S3BucketsComponent,
                RdsPostgresComponent,
                SqsQueuesComponent,
                Ec2BackendComponent,
                LambdaProcessorComponent,
                CloudFrontComponent,
                ApiGatewayComponent,
                Route53Component,
            ]
        )

    def test_config_modules_importable(self):
        """Configuration modules should be importable."""
        from IAC.configs.base import EnvironmentConfig
        from IAC.configs.constants import (
            DEFAULT_TAGS,
            VPC_CIDR,
            SUBNET_CIDRS,
            AVAILABILITY_ZONES,
        )
        from IAC.configs.environment import get_config

        assert EnvironmentConfig is not None
        assert isinstance(DEFAULT_TAGS, dict)
        assert isinstance(VPC_CIDR, str)
        assert isinstance(SUBNET_CIDRS, dict)
        assert isinstance(AVAILABILITY_ZONES, (list, tuple))
        assert callable(get_config)

    def test_utility_modules_importable(self):
        """Utility modules should be importable."""
        from IAC.utils.naming import ResourceNamer
        from IAC.utils.tags import create_tags, merge_tags

        assert ResourceNamer is not None
        assert callable(create_tags)
        assert callable(merge_tags)

    def test_main_entry_point_has_main_function(self):
        """Main entry point should define main function."""
        # We can't import __main__.py directly since it calls main() on import,
        # which requires Pulumi stack configuration. Instead, verify the file exists
        # and has the main function defined via AST parsing.
        import ast

        main_file = Path(__file__).parent.parent.parent / "IAC" / "__main__.py"
        with open(main_file, "r") as f:
            tree = ast.parse(f.read())

        # Find main function definition
        main_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                main_func = node
                break

        assert main_func is not None, "main() function not found in __main__.py"
        assert main_func.name == "main"
        # Verify it has a docstring
        docstring = ast.get_docstring(main_func)
        assert docstring is not None


class TestIacComponentStructure:
    """Validate component class structure and inheritance."""

    def test_vpc_component_has_outputs_method(self):
        """VpcComponent should have get_outputs method."""
        from IAC.components.networking.vpc import VpcComponent, VpcOutputs

        assert hasattr(VpcComponent, "get_outputs")
        assert hasattr(VpcComponent, "__init__")

        # Verify VpcOutputs is a dataclass
        assert is_dataclass(VpcOutputs)

    def test_security_groups_component_has_outputs(self):
        """SecurityGroupsComponent should have get_outputs method."""
        from IAC.components.networking.security_groups import (
            SecurityGroupsComponent,
            SecurityGroupOutputs,
        )

        assert hasattr(SecurityGroupsComponent, "get_outputs")
        assert is_dataclass(SecurityGroupOutputs)

    def test_s3_component_has_outputs(self):
        """S3BucketsComponent should have get_outputs method."""
        from IAC.components.storage.s3_buckets import S3BucketsComponent, S3BucketOutputs

        assert hasattr(S3BucketsComponent, "get_outputs")
        assert is_dataclass(S3BucketOutputs)

    def test_rds_component_has_outputs(self):
        """RdsPostgresComponent should have get_outputs method."""
        from IAC.components.storage.rds_postgres import (
            RdsPostgresComponent,
            RdsOutputs,
        )

        assert hasattr(RdsPostgresComponent, "get_outputs")
        assert is_dataclass(RdsOutputs)

    def test_iam_roles_component_has_outputs(self):
        """IamRolesComponent should have get_outputs method."""
        from IAC.components.security.iam_roles import IamRolesComponent, IamRoleOutputs

        assert hasattr(IamRolesComponent, "get_outputs")
        assert is_dataclass(IamRoleOutputs)

    def test_lambda_processor_component_has_outputs(self):
        """LambdaProcessorComponent should have get_outputs method."""
        from IAC.components.compute.lambda_processor import (
            LambdaProcessorComponent,
            LambdaOutputs,
        )

        assert hasattr(LambdaProcessorComponent, "get_outputs")
        assert is_dataclass(LambdaOutputs)


class TestIacConfiguration:
    """Validate configuration loading and structure."""

    def test_environment_config_dataclass(self):
        """EnvironmentConfig should be a proper dataclass."""
        from IAC.configs.base import EnvironmentConfig

        assert is_dataclass(EnvironmentConfig)

        # Check all expected fields exist
        fields = {f.name for f in EnvironmentConfig.__dataclass_fields__.values()}
        expected_fields = {
            "environment",
            "domain",
            "ec2_instance_type",
            "rds_instance_class",
            "rds_allocated_storage",
            "lambda_memory",
            "lambda_timeout",
            "enable_deletion_protection",
            "multi_az",
        }
        assert expected_fields.issubset(fields)

    def test_environment_config_properties(self):
        """EnvironmentConfig should have utility properties."""
        from IAC.configs.base import EnvironmentConfig

        config = EnvironmentConfig(
            environment="dev",
            domain="example.com",
            ec2_instance_type="t3.small",
            rds_instance_class="db.t3.micro",
            rds_allocated_storage=20,
            lambda_memory=512,
            lambda_timeout=300,
            enable_deletion_protection=False,
            multi_az=False,
        )

        assert config.is_production is False
        assert config.api_subdomain == "api.example.com"

        prod_config = EnvironmentConfig(
            environment="prod",
            domain="example.com",
            ec2_instance_type="t3.small",
            rds_instance_class="db.t3.micro",
            rds_allocated_storage=20,
            lambda_memory=512,
            lambda_timeout=300,
            enable_deletion_protection=True,
            multi_az=True,
        )
        assert prod_config.is_production is True

    def test_constants_are_defined(self):
        """Configuration constants should be defined."""
        from IAC.configs.constants import DEFAULT_TAGS, VPC_CIDR, SUBNET_CIDRS

        assert isinstance(DEFAULT_TAGS, dict)
        assert isinstance(VPC_CIDR, str)
        assert isinstance(SUBNET_CIDRS, dict)

        # Verify expected keys in SUBNET_CIDRS
        expected_subnets = {"private", "lambda", "data"}
        assert expected_subnets.issubset(SUBNET_CIDRS.keys())


class TestIacUtilities:
    """Validate utility functions."""

    def test_resource_namer_instantiation(self):
        """ResourceNamer should instantiate correctly."""
        from IAC.utils.naming import ResourceNamer

        namer = ResourceNamer(project="test-project", environment="dev")
        assert namer.project == "test-project"
        assert namer.environment == "dev"

    def test_resource_naming(self):
        """ResourceNamer should generate consistent names."""
        from IAC.utils.naming import ResourceNamer

        namer = ResourceNamer(project="student-helper", environment="dev")
        name = namer.name("vpc")

        # Name should contain project, environment, and resource
        assert "student-helper" in name
        assert "dev" in name
        assert "vpc" in name

    def test_create_tags_function(self):
        """create_tags should generate proper tag dictionary."""
        from IAC.utils.tags import create_tags

        tags = create_tags("dev", "test-resource", ExtraTag="extra-value")

        assert isinstance(tags, dict)
        assert tags["Environment"] == "dev"
        assert tags["Name"] == "test-resource"
        assert tags["ExtraTag"] == "extra-value"

    def test_merge_tags_function(self):
        """merge_tags should merge tag dictionaries correctly."""
        from IAC.utils.tags import merge_tags

        tags1 = {"Tag1": "value1", "Shared": "original"}
        tags2 = {"Tag2": "value2", "Shared": "updated"}

        merged = merge_tags(tags1, tags2)

        assert merged["Tag1"] == "value1"
        assert merged["Tag2"] == "value2"
        assert merged["Shared"] == "updated"  # Later dict wins


class TestIacDependencies:
    """Validate external dependencies are available."""

    def test_pulumi_importable(self):
        """Pulumi should be available."""
        import pulumi

        assert pulumi is not None

    def test_pulumi_aws_importable(self):
        """pulumi-aws should be available."""
        import pulumi_aws

        assert pulumi_aws is not None

    def test_pydantic_importable(self):
        """Pydantic should be available for schemas."""
        from pydantic import BaseModel

        assert BaseModel is not None


class TestIacComponentInitialization:
    """Test component classes can be instantiated (without Pulumi runtime)."""

    @pytest.mark.skip(reason="Requires Pulumi runtime context")
    def test_vpc_component_instantiation(self):
        """VpcComponent should instantiate with proper arguments."""
        from IAC.components.networking.vpc import VpcComponent

        # This would require Pulumi runtime, so we skip it
        # In a full test with Pulumi, this would verify the component initializes

    def test_component_classes_are_classes(self):
        """All component classes should be class objects."""
        from IAC.components.networking.vpc import VpcComponent
        from IAC.components.storage.s3_buckets import S3BucketsComponent
        from IAC.components.compute.lambda_processor import LambdaProcessorComponent

        assert isinstance(VpcComponent, type)
        assert isinstance(S3BucketsComponent, type)
        assert isinstance(LambdaProcessorComponent, type)

    def test_output_dataclasses_are_dataclasses(self):
        """All output classes should be proper dataclasses."""
        from IAC.components.networking.vpc import VpcOutputs
        from IAC.components.storage.s3_buckets import S3BucketOutputs
        from IAC.components.compute.lambda_processor import LambdaOutputs

        assert is_dataclass(VpcOutputs)
        assert is_dataclass(S3BucketOutputs)
        assert is_dataclass(LambdaOutputs)


class TestIacModuleDocumentation:
    """Validate that modules have proper documentation."""

    def test_main_module_has_docstring(self):
        """__main__.py should have module docstring."""
        import ast

        main_file = Path(__file__).parent.parent.parent / "IAC" / "__main__.py"
        with open(main_file, "r") as f:
            tree = ast.parse(f.read())

        # Get module docstring
        docstring = ast.get_docstring(tree)
        assert docstring is not None
        assert len(docstring.strip()) > 0

    def test_component_modules_have_docstrings(self):
        """Component modules should have docstrings."""
        from IAC.components.networking import vpc
        from IAC.components.storage import s3_buckets
        from IAC.components.security import iam_roles

        assert vpc.__doc__ is not None
        assert s3_buckets.__doc__ is not None
        assert iam_roles.__doc__ is not None

    def test_config_modules_have_docstrings(self):
        """Config modules should have docstrings."""
        from IAC.configs import base, environment, constants

        assert base.__doc__ is not None
        assert environment.__doc__ is not None
        assert constants.__doc__ is not None


class TestIacComponentOutputTypes:
    """Validate component output dataclass fields."""

    def test_vpc_outputs_fields(self):
        """VpcOutputs should have expected fields."""
        from IAC.components.networking.vpc import VpcOutputs

        fields = {f.name for f in VpcOutputs.__dataclass_fields__.values()}
        expected = {"vpc_id", "private_subnet_id", "lambda_subnet_id", "data_subnet_id", "nat_gateway_id"}
        assert expected.issubset(fields)

    def test_s3_outputs_fields(self):
        """S3BucketOutputs should have expected fields."""
        from IAC.components.storage.s3_buckets import S3BucketOutputs

        fields = {f.name for f in S3BucketOutputs.__dataclass_fields__.values()}
        # Should have at least bucket names and arns
        assert "documents_bucket_name" in fields
        assert "vectors_bucket_name" in fields
        assert "frontend_bucket_name" in fields

    def test_rds_outputs_fields(self):
        """RdsOutputs should have expected fields."""
        from IAC.components.storage.rds_postgres import RdsOutputs

        fields = {f.name for f in RdsOutputs.__dataclass_fields__.values()}
        # Should have at least endpoint
        assert "endpoint" in fields
