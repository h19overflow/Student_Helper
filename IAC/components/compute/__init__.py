"""
Compute components for EC2 and Lambda.

Components:
- Ec2BackendComponent: EC2 instance for FastAPI backend
- LambdaProcessorComponent: Lambda function for document processing
"""

from IAC.components.compute.ec2_backend import Ec2BackendComponent, Ec2Outputs
from IAC.components.compute.lambda_processor import LambdaProcessorComponent, LambdaOutputs

__all__ = [
    "Ec2BackendComponent",
    "Ec2Outputs",
    "LambdaProcessorComponent",
    "LambdaOutputs",
]
