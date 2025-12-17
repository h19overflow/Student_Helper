"""
Application Load Balancer component for backend traffic distribution.

Creates:
- Internal ALB in private subnets
- Target group for EC2 backend
- HTTP listener on port 80
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.configs.constants import PORTS
from IAC.utils.tags import create_tags


@dataclass
class AlbOutputs:
    """Output values from ALB component."""
    alb_arn: pulumi.Output[str]
    alb_dns_name: pulumi.Output[str]
    listener_arn: pulumi.Output[str]
    target_group_arn: pulumi.Output[str]


class AlbComponent(pulumi.ComponentResource):
    """
    Internal Application Load Balancer for EC2 backend.

    Sits between API Gateway VPC Link and EC2 instances.
    Provides health checking and future auto-scaling support.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        vpc_id: pulumi.Input[str],
        subnet_ids: list[pulumi.Input[str]],
        security_group_id: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:compute:Alb", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # Application Load Balancer (internal, not internet-facing)
        self.alb = aws.lb.LoadBalancer(
            f"{name}-alb",
            name=f"{name}-alb",
            internal=True,  # Private ALB, accessed via VPC Link
            load_balancer_type="application",
            security_groups=[security_group_id],
            subnets=subnet_ids,
            enable_deletion_protection=False,  # Dev only
            tags=create_tags(environment, f"{name}-alb"),
            opts=child_opts,
        )

        # Target Group for EC2 instances
        self.target_group = aws.lb.TargetGroup(
            f"{name}-tg",
            name=f"{name}-tg",
            port=PORTS["fastapi"],
            protocol="HTTP",
            vpc_id=vpc_id,
            target_type="instance",
            health_check=aws.lb.TargetGroupHealthCheckArgs(
                enabled=True,
                path="/api/v1/health",
                port="traffic-port",
                protocol="HTTP",
                healthy_threshold=2,
                unhealthy_threshold=3,
                timeout=5,
                interval=30,
                matcher="200",
            ),
            tags=create_tags(environment, f"{name}-tg"),
            opts=child_opts,
        )

        # HTTP Listener
        self.listener = aws.lb.Listener(
            f"{name}-listener",
            load_balancer_arn=self.alb.arn,
            port=80,
            protocol="HTTP",
            default_actions=[
                aws.lb.ListenerDefaultActionArgs(
                    type="forward",
                    target_group_arn=self.target_group.arn,
                ),
            ],
            tags=create_tags(environment, f"{name}-listener"),
            opts=child_opts,
        )

        self.register_outputs({
            "alb_arn": self.alb.arn,
            "alb_dns_name": self.alb.dns_name,
            "listener_arn": self.listener.arn,
            "target_group_arn": self.target_group.arn,
        })

    def get_outputs(self) -> AlbOutputs:
        """Get ALB output values."""
        return AlbOutputs(
            alb_arn=self.alb.arn,
            alb_dns_name=self.alb.dns_name,
            listener_arn=self.listener.arn,
            target_group_arn=self.target_group.arn,
        )
