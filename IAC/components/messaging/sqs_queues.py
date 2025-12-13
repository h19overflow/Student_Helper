"""
SQS queues component for async document processing.

Creates:
- Main queue for document processing jobs
- Dead letter queue for failed messages
- Redrive policy for automatic retries
"""

import json
from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.configs.constants import SQS_DEFAULTS
from IAC.utils.tags import create_tags
from IAC.utils.naming import ResourceNamer


@dataclass
class SqsOutputs:
    """Output values from SQS queues component."""
    queue_url: pulumi.Output[str]
    queue_arn: pulumi.Output[str]
    dlq_url: pulumi.Output[str]
    dlq_arn: pulumi.Output[str]


class SqsQueuesComponent(pulumi.ComponentResource):
    """
    SQS queues for async document processing.

    Main queue triggers Lambda for document processing.
    Dead letter queue captures failed messages after max retries.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        namer: ResourceNamer,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:messaging:SqsQueues", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # Dead Letter Queue (must be created first for redrive policy)
        self.dlq = aws.sqs.Queue(
            f"{name}-dlq",
            name=f"{namer.name('doc-processor')}-dlq",
            message_retention_seconds=SQS_DEFAULTS["message_retention_seconds"],
            tags=create_tags(environment, f"{name}-dlq"),
            opts=child_opts,
        )

        # Main Queue with redrive policy
        self.queue = aws.sqs.Queue(
            f"{name}-queue",
            name=namer.name("doc-processor"),
            visibility_timeout_seconds=SQS_DEFAULTS["visibility_timeout_seconds"],
            message_retention_seconds=SQS_DEFAULTS["message_retention_seconds"],
            redrive_policy=self.dlq.arn.apply(
                lambda arn: json.dumps({
                    "deadLetterTargetArn": arn,
                    "maxReceiveCount": SQS_DEFAULTS["max_receive_count"],
                })
            ),
            tags=create_tags(environment, f"{name}-queue"),
            opts=child_opts,
        )

        # Allow DLQ to receive from main queue
        aws.sqs.RedriveAllowPolicy(
            f"{name}-redrive-allow",
            queue_url=self.dlq.url,
            redrive_allow_policy=self.queue.arn.apply(
                lambda arn: json.dumps({
                    "redrivePermission": "byQueue",
                    "sourceQueueArns": [arn],
                })
            ),
            opts=child_opts,
        )

        self.register_outputs({
            "queue_url": self.queue.url,
            "queue_arn": self.queue.arn,
            "dlq_url": self.dlq.url,
            "dlq_arn": self.dlq.arn,
        })

    def get_outputs(self) -> SqsOutputs:
        """Get SQS queue output values."""
        return SqsOutputs(
            queue_url=self.queue.url,
            queue_arn=self.queue.arn,
            dlq_url=self.dlq.url,
            dlq_arn=self.dlq.arn,
        )
