"""
API Gateway Component for Backend Routing.

Concept: "Expose a private backend to the internet without making the backend public."
API Gateway acts as a Managed Proxy.

The 5-Resource Dependency Chain:
1. VPC Link: Creates ENIs in your private subnets. API Gateway uses these to "tunnel" into your VPC.
2. API: The HTTP API container (protocol type, CORS settings).
3. Integration: The wiring. Tells API GW HOW to reach the backend (via VPC Link) and WHERE (the ALB Listener ARN).
4. Route: The URL map. Matches paths like "ANY /{proxy+}" and forwards to the Integration.
5. Stage: The deployment. Publishes the API and gives you a live URL. "$default" = clean URL.

CRITICAL DISTINCTION: VPC Link vs VPC Endpoint:
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ VPC Endpoint (PrivateLink):                                                         │
│   - Direction: OUTBOUND (Your VPC resources → AWS Services)                         │
│   - Purpose: Lets your private EC2/Lambda reach S3, SQS, Bedrock WITHOUT internet.  │
│   - "I'm inside the VPC, I want to reach an AWS service privately."                 │
│                                                                                      │
│ VPC Link (API Gateway Feature):                                                     │
│   - Direction: INBOUND (External AWS Service → Your VPC)                            │
│   - Purpose: Lets API Gateway (a public AWS service) reach INTO your private VPC.   │
│   - "I'm outside the VPC, I need a tunnel to get inside."                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags


@dataclass
class ApiGatewayOutputs:
    """Output values from API Gateway component."""
    api_endpoint: pulumi.Output[str]
    api_id: pulumi.Output[str]


class ApiGatewayComponent(pulumi.ComponentResource):
    """
    HTTP API Gateway with VPC Link to ALB.

    Routes all requests to FastAPI application via internal ALB.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        vpc_id: pulumi.Input[str],
        subnet_ids: list[pulumi.Input[str]],
        security_group_id: pulumi.Input[str],
        alb_listener_arn: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:edge:ApiGateway", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # VPC Link for private integration
        self.vpc_link = aws.apigatewayv2.VpcLink(
            f"{name}-vpc-link",
            name=f"{name}-vpc-link",
            subnet_ids=subnet_ids,
            security_group_ids=[security_group_id],
            tags=create_tags(environment, f"{name}-vpc-link"),
            opts=child_opts,
        )

        # HTTP API
        self.api = aws.apigatewayv2.Api(
            f"{name}-api",
            name=f"{name}-api",
            protocol_type="HTTP",
            cors_configuration=aws.apigatewayv2.ApiCorsConfigurationArgs(
                allow_origins=["*"],
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["*"],
                max_age=86400,
            ),
            tags=create_tags(environment, f"{name}-api"),
            opts=child_opts,
        )

        # Integration with ALB via VPC Link
        # HTTP_PROXY supports WebSocket upgrade requests
        self.integration = aws.apigatewayv2.Integration(
            f"{name}-integration",
            api_id=self.api.id,
            integration_type="HTTP_PROXY",
            integration_method="ANY",
            integration_uri=alb_listener_arn,
            connection_type="VPC_LINK",
            connection_id=self.vpc_link.id,
            # Integration timeout for initial HTTP requests and WebSocket handshake
            # Once WebSocket is established, connection can stay open up to 10 min idle
            timeout_milliseconds=30000,  # 30 seconds (max for HTTP API)
            # Preserve headers for WebSocket upgrade (Connection: Upgrade, Upgrade: websocket)
            payload_format_version="1.0",
            opts=child_opts,
        )

        # Catch-all route
        self.route = aws.apigatewayv2.Route(
            f"{name}-route",
            api_id=self.api.id,
            route_key="ANY /{proxy+}",
            target=self.integration.id.apply(lambda id: f"integrations/{id}"),
            opts=child_opts,
        )

        # Root route (for /api/v1/health etc without proxy)
        self.root_route = aws.apigatewayv2.Route(
            f"{name}-root-route",
            api_id=self.api.id,
            route_key="ANY /",
            target=self.integration.id.apply(lambda id: f"integrations/{id}"),
            opts=child_opts,
        )

        # Default stage with auto-deploy
        self.stage = aws.apigatewayv2.Stage(
            f"{name}-stage",
            api_id=self.api.id,
            name="$default",
            auto_deploy=True,
            tags=create_tags(environment, f"{name}-stage"),
            opts=child_opts,
        )

        self.register_outputs({
            "api_endpoint": self.api.api_endpoint,
            "api_id": self.api.id,
        })

    def get_outputs(self) -> ApiGatewayOutputs:
        """Get API Gateway output values."""
        return ApiGatewayOutputs(
            api_endpoint=self.api.api_endpoint,
            api_id=self.api.id,
        )
