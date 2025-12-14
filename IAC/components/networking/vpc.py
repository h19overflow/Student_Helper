"""
VPC component resource for network infrastructure.

Creates VPC with three subnets:
- Private subnet (10.0.1.0/24): EC2 backend
- Lambda subnet (10.0.2.0/24): Lambda processor
- Data subnet (10.0.3.0/24): RDS PostgreSQL
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.configs.constants import VPC_CIDR, SUBNET_CIDRS, AVAILABILITY_ZONES
from IAC.utils.tags import create_tags


@dataclass
class VpcOutputs:
    """Output values from VPC component."""
    vpc_id: pulumi.Output[str]
    private_subnet_id: pulumi.Output[str]
    lambda_subnet_id: pulumi.Output[str]
    data_subnet_id: pulumi.Output[str]


class VpcComponent(pulumi.ComponentResource):
    """
    VPC component with subnets and NAT gateway.

    Creates a VPC with three private subnets for compute and data layers,
    plus a NAT gateway for outbound internet access from Lambda.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:networking:Vpc", name, None, opts)
        self.environment = environment

        child_opts = pulumi.ResourceOptions(parent=self)

        # Create VPC
        self.vpc = aws.ec2.Vpc(
            f"{name}-vpc",
            cidr_block=VPC_CIDR,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            tags=create_tags(environment, f"{name}-vpc"),
            opts=child_opts,
        )

        # Create Internet Gateway (for NAT Gateway)
        self.igw = aws.ec2.InternetGateway(
            f"{name}-igw",
            vpc_id=self.vpc.id,
            tags=create_tags(environment, f"{name}-igw"),
            opts=child_opts,
        )

        # Create public subnet for NAT Gateway
        self.public_subnet = aws.ec2.Subnet(
            f"{name}-public-subnet",
            vpc_id=self.vpc.id,
            cidr_block="10.0.0.0/24",
            availability_zone=AVAILABILITY_ZONES[0],
            map_public_ip_on_launch=True,
            tags=create_tags(environment, f"{name}-public-subnet"),
            opts=child_opts,
        )

        # Create private subnets
        self.private_subnet = aws.ec2.Subnet(
            f"{name}-private-subnet",
            vpc_id=self.vpc.id,
            cidr_block=SUBNET_CIDRS["private"],
            availability_zone=AVAILABILITY_ZONES[0],
            tags=create_tags(environment, f"{name}-private-subnet"),
            opts=child_opts,
        )

        self.lambda_subnet = aws.ec2.Subnet(
            f"{name}-lambda-subnet",
            vpc_id=self.vpc.id,
            cidr_block=SUBNET_CIDRS["lambda"],
            availability_zone=AVAILABILITY_ZONES[0],
            tags=create_tags(environment, f"{name}-lambda-subnet"),
            opts=child_opts,
        )

        self.data_subnet = aws.ec2.Subnet(
            f"{name}-data-subnet",
            vpc_id=self.vpc.id,
            cidr_block=SUBNET_CIDRS["data"],
            availability_zone=AVAILABILITY_ZONES[0],
            tags=create_tags(environment, f"{name}-data-subnet"),
            opts=child_opts,
        )

        # Create route tables
        self._create_route_tables(name, child_opts)

        self.register_outputs({
            "vpc_id": self.vpc.id,
            "private_subnet_id": self.private_subnet.id,
            "lambda_subnet_id": self.lambda_subnet.id,
            "data_subnet_id": self.data_subnet.id,
        })

    def _create_route_tables(
        self,
        name: str,
        opts: pulumi.ResourceOptions,
    ) -> None:
        """Create route tables for public and private subnets."""
        # Public route table (Internet Gateway)
        public_rt = aws.ec2.RouteTable(
            f"{name}-public-rt",
            vpc_id=self.vpc.id,
            routes=[
                aws.ec2.RouteTableRouteArgs(
                    cidr_block="0.0.0.0/0",
                    gateway_id=self.igw.id,
                ),
            ],
            tags=create_tags(self.environment, f"{name}-public-rt"),
            opts=opts,
        )

        aws.ec2.RouteTableAssociation(
            f"{name}-public-rt-assoc",
            subnet_id=self.public_subnet.id,
            route_table_id=public_rt.id,
            opts=opts,
        )

        # Private route table (VPC-only routing)
        # All external access (Bedrock, etc.) goes through VPC Endpoints
        private_rt = aws.ec2.RouteTable(
            f"{name}-private-rt",
            vpc_id=self.vpc.id,
            routes=[],  # No default internet route - VPC Endpoints only
            tags=create_tags(self.environment, f"{name}-private-rt"),
            opts=opts,
        )

        # Associate private subnets with private route table
        for subnet_name, subnet in [
            ("private", self.private_subnet),
            ("lambda", self.lambda_subnet),
            ("data", self.data_subnet),
        ]:
            aws.ec2.RouteTableAssociation(
                f"{name}-{subnet_name}-rt-assoc",
                subnet_id=subnet.id,
                route_table_id=private_rt.id,
                opts=opts,
            )

    def get_outputs(self) -> VpcOutputs:
        """Get VPC output values."""
        return VpcOutputs(
            vpc_id=self.vpc.id,
            private_subnet_id=self.private_subnet.id,
            lambda_subnet_id=self.lambda_subnet.id,
            data_subnet_id=self.data_subnet.id,
        )
