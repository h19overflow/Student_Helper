"""
WebSocket API Gateway component for real-time chat.

Creates:
- WebSocket API (API Gateway v2)
- VPC Link V1 for private NLB access
- Routes for WebSocket connections

Note: WebSocket APIs require VPC Link V1 (not V2) with NLB target.
HTTP APIs use VPC Link V2 with ALB.
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags


@dataclass
class WebSocketApiGatewayOutputs:
    """Output values from WebSocket API Gateway component."""
    api_endpoint: pulumi.Output[str]
    api_id: pulumi.Output[str]


class WebSocketApiGatewayComponent(pulumi.ComponentResource):
    """
    WebSocket API Gateway with VPC Link V1 to NLB.

    Routes WebSocket connections to FastAPI WebSocket endpoints via internal NLB.
    VPC Link V1 is required for WebSocket APIs (V2 only works with HTTP APIs).
    """

    def __init__(
        self,
        name: str,
        environment: str,
        nlb_arn: pulumi.Input[str],
        nlb_dns_name: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:edge:WebSocketApiGateway", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # VPC Link V1 for private integration (required for WebSocket API)
        # VPC Link V2 (apigatewayv2.VpcLink) only works with HTTP APIs
        self.vpc_link = aws.apigateway.VpcLink(
            f"{name}-ws-vpc-link",
            name=f"{name}-ws-vpc-link",
            target_arn=nlb_arn,  # VPC Link V1 requires single NLB ARN (not array)
            tags=create_tags(environment, f"{name}-ws-vpc-link"),
            opts=child_opts,
        )

        # WebSocket API
        self.api = aws.apigatewayv2.Api(
            f"{name}-ws-api",
            name=f"{name}-ws-api",
            protocol_type="WEBSOCKET",  # WebSocket protocol
            route_selection_expression="$request.body.action",
            tags=create_tags(environment, f"{name}-ws-api"),
            opts=child_opts,
        )

        # Integration with NLB via VPC Link V1
        # For WebSocket API with VPC Link, integration_uri is the load balancer HTTP URL
        self.integration = aws.apigatewayv2.Integration(
            f"{name}-ws-integration",
            api_id=self.api.id,
            integration_type="HTTP_PROXY",
            integration_method="ANY",
            # VPC Link V1 requires HTTP URL to NLB (not ARN like VPC Link V2)
            integration_uri=nlb_dns_name.apply(lambda dns: f"http://{dns}:8000"),
            connection_type="VPC_LINK",
            connection_id=self.vpc_link.id,
            timeout_milliseconds=29000,  # Max for WebSocket
            payload_format_version="1.0",
            opts=child_opts,
        )

        # $connect route (WebSocket connection initiation)
        self.connect_route = aws.apigatewayv2.Route(
            f"{name}-ws-connect",
            api_id=self.api.id,
            route_key="$connect",
            target=self.integration.id.apply(lambda id: f"integrations/{id}"),
            opts=child_opts,
        )

        # $disconnect route (WebSocket disconnection)
        self.disconnect_route = aws.apigatewayv2.Route(
            f"{name}-ws-disconnect",
            api_id=self.api.id,
            route_key="$disconnect",
            target=self.integration.id.apply(lambda id: f"integrations/{id}"),
            opts=child_opts,
        )

        # $default route (all other messages)
        self.default_route = aws.apigatewayv2.Route(
            f"{name}-ws-default",
            api_id=self.api.id,
            route_key="$default",
            target=self.integration.id.apply(lambda id: f"integrations/{id}"),
            opts=child_opts,
        )

        # Production stage
        self.stage = aws.apigatewayv2.Stage(
            f"{name}-ws-stage",
            api_id=self.api.id,
            name="production",
            auto_deploy=True,
            tags=create_tags(environment, f"{name}-ws-stage"),
            opts=child_opts,
        )

        # Deployment
        self.deployment = aws.apigatewayv2.Deployment(
            f"{name}-ws-deployment",
            api_id=self.api.id,
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[
                    self.connect_route,
                    self.disconnect_route,
                    self.default_route,
                ],
            ),
        )

        self.register_outputs({
            "api_endpoint": self.stage.invoke_url,
            "api_id": self.api.id,
        })

    def get_outputs(self) -> WebSocketApiGatewayOutputs:
        """Get WebSocket API Gateway output values."""
        return WebSocketApiGatewayOutputs(
            api_endpoint=self.stage.invoke_url,
            api_id=self.api.id,
        )
