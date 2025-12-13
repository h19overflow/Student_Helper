"""
Edge components for CDN and API routing.

Components:
- CloudFrontComponent: CDN distribution for frontend
- ApiGatewayComponent: HTTP API with VPC Link to backend
"""

from IAC.components.edge.cloudfront import CloudFrontComponent
from IAC.components.edge.api_gateway import ApiGatewayComponent, ApiGatewayOutputs

__all__ = [
    "CloudFrontComponent",
    "ApiGatewayComponent",
    "ApiGatewayOutputs",
]
