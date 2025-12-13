"""
Messaging components for async job processing.

Components:
- SqsQueuesComponent: Main queue and dead letter queue
"""

from IAC.components.messaging.sqs_queues import SqsQueuesComponent, SqsOutputs

__all__ = [
    "SqsQueuesComponent",
    "SqsOutputs",
]
