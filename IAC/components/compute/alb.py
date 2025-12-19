"""
Application Load Balancer Component for Backend Traffic Distribution.

Core Jobs:
1. Distribute Traffic: Spread requests across multiple EC2 instances.
2. Health Check: Constantly ping servers. If one dies, stop sending traffic there.
3. Stable Endpoint: EC2s come and go, but the ALB DNS stays the same.

The 3-Resource Chain:
1. Load Balancer: The "building". Has a DNS name. Receives all incoming traffic.
2. Listener: The "door/ear". Binds to a PORT (e.g., 80). Defines WHAT to do when traffic arrives (forward, redirect, etc.).
   - Without a Listener, the ALB is DEAF. It ignores all traffic.
   - Multiple Listeners = Multiple doors (e.g., port 80 redirects to 443, port 443 forwards to EC2s).
3. Target Group: The "pool of servers". Contains healthy EC2 instances. ALB picks one and forwards the request.

Connection to API Gateway / CloudFront:
- The Listener exposes an ARN (unique identifier).
- API Gateway's Integration uses `integration_uri=listener_arn` to know WHERE to forward traffic.
- CloudFront uses the ALB's DNS name as an Origin.

WebSocket Considerations:
- idle_timeout=600: Keep connections alive for 10 minutes even if no data flows.
- stickiness: Ensure the same client always hits the same server (stateful WebSocket connections).
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

        # Internal Application Load Balancer (accessed via API Gateway VPC Link)
        self.alb = aws.lb.LoadBalancer(
            f"{name}-alb",
            name=f"{name}-alb",
            internal=True,  # Internal ALB, accessed via VPC Link from API Gateway
            load_balancer_type="application",
            security_groups=[security_group_id],
            subnets=subnet_ids,
            enable_deletion_protection=False,  # Dev only
            # Increase idle timeout for WebSocket connections (default 60s)
            idle_timeout=600,  # 10 minutes - matches API Gateway idle timeout
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
            # Enable sticky sessions for WebSocket connections
            stickiness=aws.lb.TargetGroupStickinessArgs(
                enabled=True,
                type="lb_cookie",
                cookie_duration=86400,  # 24 hours
            ),
            # Increase deregistration delay for graceful WebSocket shutdown
            deregistration_delay=300,  # 5 minutes (default is 300)
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
