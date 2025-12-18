"""
Network Load Balancer component for WebSocket traffic.

Creates:
- Internal NLB in private subnets
- Target group for EC2 backend (TCP)
- TCP listener on port 8000

Note: NLB required for WebSocket API with VPC Link V1.
ALB uses VPC Link V2 (HTTP API), NLB uses VPC Link V1 (WebSocket API).
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.configs.constants import PORTS
from IAC.utils.tags import create_tags


@dataclass
class NlbOutputs:
    """Output values from NLB component."""
    nlb_arn: pulumi.Output[str]
    nlb_dns_name: pulumi.Output[str]
    listener_arn: pulumi.Output[str]
    target_group_arn: pulumi.Output[str]


class NlbComponent(pulumi.ComponentResource):
    """
    Internal Network Load Balancer for EC2 backend WebSocket traffic.

    Used specifically for WebSocket API Gateway private integration via VPC Link V1.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        vpc_id: pulumi.Input[str],
        subnet_ids: list[pulumi.Input[str]],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:compute:Nlb", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # Network Load Balancer (internal)
        # NLB doesn't use security groups - operates at Layer 4 (TCP)
        # Shorten name to avoid 32-char AWS limit
        nlb_name = name.replace("-websocket", "-ws")
        self.nlb = aws.lb.LoadBalancer(
            f"{name}-nlb",
            name=f"{nlb_name}-nlb",
            internal=True,  # Private NLB for VPC Link V1
            load_balancer_type="network",
            subnets=subnet_ids,
            enable_deletion_protection=False,  # Dev only
            enable_cross_zone_load_balancing=True,
            tags=create_tags(environment, f"{name}-nlb"),
            opts=child_opts,
        )

        # Target Group for EC2 instances (TCP protocol)
        self.target_group = aws.lb.TargetGroup(
            f"{name}-nlb-tg",
            name=f"{nlb_name}-tg",  # Shortened to fit 32-char AWS limit
            port=PORTS["fastapi"],
            protocol="TCP",  # Layer 4 protocol for WebSocket
            vpc_id=vpc_id,
            target_type="instance",
            deregistration_delay=30,  # Faster than ALB for TCP
            health_check=aws.lb.TargetGroupHealthCheckArgs(
                enabled=True,
                port="traffic-port",
                protocol="HTTP",  # Use HTTP health check instead of TCP
                path="/api/v1/health",  # Same as ALB health check
                healthy_threshold=2,
                unhealthy_threshold=2,
                interval=30,
                timeout=10,
                matcher="200",
            ),
            tags=create_tags(environment, f"{name}-nlb-tg"),
            opts=child_opts,
        )

        # TCP Listener (Layer 4)
        self.listener = aws.lb.Listener(
            f"{name}-nlb-listener",
            load_balancer_arn=self.nlb.arn,
            port=PORTS["fastapi"],
            protocol="TCP",
            default_actions=[
                aws.lb.ListenerDefaultActionArgs(
                    type="forward",
                    target_group_arn=self.target_group.arn,
                ),
            ],
            tags=create_tags(environment, f"{name}-nlb-listener"),
            opts=child_opts,
        )

        self.register_outputs({
            "nlb_arn": self.nlb.arn,
            "nlb_dns_name": self.nlb.dns_name,
            "listener_arn": self.listener.arn,
            "target_group_arn": self.target_group.arn,
        })

    def get_outputs(self) -> NlbOutputs:
        """Get NLB output values."""
        return NlbOutputs(
            nlb_arn=self.nlb.arn,
            nlb_dns_name=self.nlb.dns_name,
            listener_arn=self.listener.arn,
            target_group_arn=self.target_group.arn,
        )
