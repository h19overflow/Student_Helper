"""
Networking components for VPC infrastructure.

Components:
- VpcComponent: VPC with subnets, NAT gateway, route tables
- SecurityGroupsComponent: Security groups for backend, lambda, database, endpoints
- VpcEndpointsComponent: S3, SQS, Secrets Manager VPC endpoints
"""

from IAC.components.networking.vpc import VpcComponent, VpcOutputs
from IAC.components.networking.security_groups import SecurityGroupsComponent, SecurityGroupOutputs
from IAC.components.networking.vpc_endpoints import VpcEndpointsComponent

__all__ = [
    "VpcComponent",
    "VpcOutputs",
    "SecurityGroupsComponent",
    "SecurityGroupOutputs",
    "VpcEndpointsComponent",
]
