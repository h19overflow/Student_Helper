"""
Security Groups Component for Network Access Control.

Architectural Steps & Flow:
1. Create "Shell" Security Groups:
   - Identitiy Badges: We first create the SG objects (Backend, Database, ALB, etc.) without rules. This allows them to exist so they can be referenced by ID.

2. Define Rules (Micro-Segmentation):
   - Ingress (Inbound): "Who can enter?" defined by referencing Source SGs (Identity-based) rather than IPs where possible.
   - Egress (Outbound): "Who can I talk to?" generally open for backend services to fetch updates/APIs.

3. Specific Access Patterns:
   - ALB: Accepts HTTP from CloudFront (via Prefix List) & forwards to Backend.
   - Backend: Accepts traffic ONLY from ALB (on port 8000).
   - Database: Extremely restricted. Accepts traffic ONLY from Backend/Lambda (on port 5432). Rejects everything else.
   - Self-Reference: Used for internal VPC Link communication.

4. Stateful Nature:
   - Remember: Security Groups are stateful. Allowing an Inbound request AUTOMATICALLY allows the Outbound reply.
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.configs.constants import PORTS
from IAC.utils.tags import create_tags


@dataclass
class SecurityGroupOutputs:
    """Output values from security groups component."""
    backend_sg_id: pulumi.Output[str]
    lambda_sg_id: pulumi.Output[str]
    database_sg_id: pulumi.Output[str]
    endpoints_sg_id: pulumi.Output[str]
    alb_sg_id: pulumi.Output[str]


class SecurityGroupsComponent(pulumi.ComponentResource):
    """
    Security groups component for network access control.

    Implements least-privilege security group rules:
    - Backend accepts traffic from API Gateway VPC Link
    - Lambda has outbound-only access (SQS trigger is AWS managed)
    - Database accepts connections only from backend and lambda
    - VPC endpoints accept HTTPS from backend and lambda
    """

    def __init__(
        self,
        name: str,
        environment: str,
        vpc_id: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:networking:SecurityGroups", name, None, opts)
        self.environment = environment

        child_opts = pulumi.ResourceOptions(parent=self)

        # Backend security group
        self.backend_sg = aws.ec2.SecurityGroup(
            f"{name}-backend-sg",
            description="Security group for FastAPI backend EC2",
            vpc_id=vpc_id,
            tags=create_tags(environment, f"{name}-backend-sg"),
            opts=child_opts,
        )

        # Lambda security group
        self.lambda_sg = aws.ec2.SecurityGroup(
            f"{name}-lambda-sg",
            description="Security group for document processor Lambda",
            vpc_id=vpc_id,
            tags=create_tags(environment, f"{name}-lambda-sg"),
            opts=child_opts,
        )

        # Database security group
        self.database_sg = aws.ec2.SecurityGroup(
            f"{name}-database-sg",
            description="Security group for RDS PostgreSQL",
            vpc_id=vpc_id,
            tags=create_tags(environment, f"{name}-database-sg"),
            opts=child_opts,
        )

        # VPC endpoints security group
        self.endpoints_sg = aws.ec2.SecurityGroup(
            f"{name}-endpoints-sg",
            description="Security group for VPC endpoints",
            vpc_id=vpc_id,
            tags=create_tags(environment, f"{name}-endpoints-sg"),
            opts=child_opts,
        )

        # ALB security group
        self.alb_sg = aws.ec2.SecurityGroup(
            f"{name}-alb-sg",
            description="Security group for Application Load Balancer",
            vpc_id=vpc_id,
            tags=create_tags(environment, f"{name}-alb-sg"),
            opts=child_opts,
        )

        self._create_rules(name, child_opts)

        self.register_outputs({
            "backend_sg_id": self.backend_sg.id,
            "lambda_sg_id": self.lambda_sg.id,
            "database_sg_id": self.database_sg.id,
            "endpoints_sg_id": self.endpoints_sg.id,
            "alb_sg_id": self.alb_sg.id,
        })

    def _create_rules(
        self,
        name: str,
        opts: pulumi.ResourceOptions,
    ) -> None:
        """Create security group rules."""
        # Backend: Allow inbound on FastAPI port from ALB
        aws.vpc.SecurityGroupIngressRule(
            f"{name}-backend-ingress-fastapi",
            security_group_id=self.backend_sg.id,
            ip_protocol="tcp",
            from_port=PORTS["fastapi"],
            to_port=PORTS["fastapi"],
            referenced_security_group_id=self.alb_sg.id,
            description="FastAPI from ALB",
            opts=opts,
        )

        # Backend: Allow all outbound
        aws.vpc.SecurityGroupEgressRule(
            f"{name}-backend-egress-all",
            security_group_id=self.backend_sg.id,
            ip_protocol="-1",
            cidr_ipv4="0.0.0.0/0",
            description="All outbound traffic",
            opts=opts,
        )

        # Lambda: Allow all outbound (SQS trigger is AWS managed)
        aws.vpc.SecurityGroupEgressRule(
            f"{name}-lambda-egress-all",
            security_group_id=self.lambda_sg.id,
            ip_protocol="-1",
            cidr_ipv4="0.0.0.0/0",
            description="All outbound traffic",
            opts=opts,
        )

        # Database: Allow PostgreSQL from backend
        aws.vpc.SecurityGroupIngressRule(
            f"{name}-database-ingress-backend",
            security_group_id=self.database_sg.id,
            ip_protocol="tcp",
            from_port=PORTS["postgres"],
            to_port=PORTS["postgres"],
            referenced_security_group_id=self.backend_sg.id,
            description="PostgreSQL from backend",
            opts=opts,
        )

        # Database: Allow PostgreSQL from lambda
        aws.vpc.SecurityGroupIngressRule(
            f"{name}-database-ingress-lambda",
            security_group_id=self.database_sg.id,
            ip_protocol="tcp",
            from_port=PORTS["postgres"],
            to_port=PORTS["postgres"],
            referenced_security_group_id=self.lambda_sg.id,
            description="PostgreSQL from lambda",
            opts=opts,
        )

        # Endpoints: Allow HTTPS from backend
        aws.vpc.SecurityGroupIngressRule(
            f"{name}-endpoints-ingress-backend",
            security_group_id=self.endpoints_sg.id,
            ip_protocol="tcp",
            from_port=PORTS["https"],
            to_port=PORTS["https"],
            referenced_security_group_id=self.backend_sg.id,
            description="HTTPS from backend",
            opts=opts,
        )

        # Endpoints: Allow HTTPS from lambda
        aws.vpc.SecurityGroupIngressRule(
            f"{name}-endpoints-ingress-lambda",
            security_group_id=self.endpoints_sg.id,
            ip_protocol="tcp",
            from_port=PORTS["https"],
            to_port=PORTS["https"],
            referenced_security_group_id=self.lambda_sg.id,
            description="HTTPS from lambda",
            opts=opts,
        )

        # Get CloudFront Managed Prefix List
        cloudfront_prefix_list = aws.ec2.get_managed_prefix_list(
            name="com.amazonaws.global.cloudfront.origin-facing"
        )

        # ALB: Allow inbound HTTP from CloudFront (Internet-facing ALB restricted by Prefix List)
        aws.vpc.SecurityGroupIngressRule(
            f"{name}-alb-ingress-http",
            security_group_id=self.alb_sg.id,
            ip_protocol="tcp",
            from_port=PORTS["http"],
            to_port=PORTS["http"],
            prefix_list_id=cloudfront_prefix_list.id,
            description="HTTP from CloudFront",
            opts=opts,
        )

        # ALB: Allow outbound to backend
        aws.vpc.SecurityGroupEgressRule(
            f"{name}-alb-egress-backend",
            security_group_id=self.alb_sg.id,
            ip_protocol="tcp",
            from_port=PORTS["fastapi"],
            to_port=PORTS["fastapi"],
            referenced_security_group_id=self.backend_sg.id,
            description="To backend FastAPI",
            opts=opts,
        )

        # ALB: Allow outbound to self (VPC Link ENI → ALB on port 80)
        # VPC Link uses the same security group as ALB
        aws.vpc.SecurityGroupEgressRule(
            f"{name}-alb-egress-self",
            security_group_id=self.alb_sg.id,
            ip_protocol="tcp",
            from_port=PORTS["http"],
            to_port=PORTS["http"],
            referenced_security_group_id=self.alb_sg.id,
            description="VPC Link to ALB (self-reference)",
            opts=opts,
        )

    def get_outputs(self) -> SecurityGroupOutputs:
        """Get security group output values."""
        return SecurityGroupOutputs(
            backend_sg_id=self.backend_sg.id,
            lambda_sg_id=self.lambda_sg.id,
            database_sg_id=self.database_sg.id,
            endpoints_sg_id=self.endpoints_sg.id,
            alb_sg_id=self.alb_sg.id,
        )
