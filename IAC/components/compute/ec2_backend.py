"""
EC2 Backend Component for FastAPI Application.

This is the FINAL DESTINATION of an inbound request (CloudFront → API Gateway → ALB → EC2).

Key Components:
1. AMI (Amazon Machine Image): The OS/software template. We use Amazon Linux 2023 with Docker pre-installed.
2. User Data: Bootstrap script that runs ONCE at first boot. Installs dependencies, creates directories, sets up systemd service.
3. Instance Profile: Links an IAM Role to the EC2, granting permissions to call AWS APIs (Secrets Manager, S3, etc.).
4. Placement:
   - subnet_id: Lives in PRIVATE subnet (no public IP, no direct internet).
   - security_group_id: Firewall. Only allows inbound from ALB on port 8000.
5. Storage (root_block_device): 30GB gp3 SSD, encrypted at rest.
6. IMDSv2 (http_tokens="required"): Secures metadata service against SSRF attacks. Always enable this.
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags
from IAC.configs.base import EnvironmentConfig


@dataclass
class Ec2Outputs:
    """Output values from EC2 component."""
    instance_id: pulumi.Output[str]
    private_ip: pulumi.Output[str]


class Ec2BackendComponent(pulumi.ComponentResource):
    """
    EC2 instance for FastAPI backend application.

    Runs in private subnet with access via API Gateway VPC Link.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        config: EnvironmentConfig,
        subnet_id: pulumi.Input[str],
        security_group_id: pulumi.Input[str],
        instance_profile_name: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:compute:Ec2Backend", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        # Get latest Amazon Linux 2023 ECS-optimized AMI (has Docker pre-installed)
        ami = aws.ec2.get_ami(
            most_recent=True,
            owners=["amazon"],
            filters=[
                aws.ec2.GetAmiFilterArgs(
                    name="name",
                    values=["al2023-ami-ecs-hvm-*-x86_64"],
                ),
                aws.ec2.GetAmiFilterArgs(
                    name="virtualization-type",
                    values=["hvm"],
                ),
            ],
        )

        # User data script for bootstrapping
        user_data = """#!/bin/bash
set -e

# Update system
apt-get update && apt-get upgrade -y

# Install Python 3.12 and dependencies
apt-get install -y python3.12 python3.12-venv python3-pip git

# Create application directory
mkdir -p /opt/studenthelper
cd /opt/studenthelper

# Create systemd service (application deployment handled separately)
cat > /etc/systemd/system/studenthelper.service << 'EOF'
[Unit]
Description=Student Helper FastAPI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/studenthelper
ExecStart=/usr/bin/python3.12 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable studenthelper

# CloudWatch agent for logs
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb
rm amazon-cloudwatch-agent.deb

echo "Bootstrap complete"
"""

        # CloudWatch Log Group
        self.log_group = aws.cloudwatch.LogGroup(
            f"{name}-logs",
            name=f"/ec2/{name}",
            retention_in_days=30,
            tags=create_tags(environment, f"{name}-logs"),
            opts=child_opts,
        )

        # EC2 Instance
        self.instance = aws.ec2.Instance(
            f"{name}-instance",
            ami=ami.id,
            instance_type=config.ec2_instance_type,
            subnet_id=subnet_id,
            vpc_security_group_ids=[security_group_id],
            iam_instance_profile=instance_profile_name,
            user_data=user_data,
            root_block_device=aws.ec2.InstanceRootBlockDeviceArgs(
                volume_size=30,
                volume_type="gp3",
                encrypted=True,
            ),
            metadata_options=aws.ec2.InstanceMetadataOptionsArgs(
                http_tokens="required",  # IMDSv2
                http_endpoint="enabled",
            ),
            tags=create_tags(environment, f"{name}-backend"),
            opts=child_opts,
        )

        self.register_outputs({
            "instance_id": self.instance.id,
            "private_ip": self.instance.private_ip,
        })

    def get_outputs(self) -> Ec2Outputs:
        """Get EC2 output values."""
        return Ec2Outputs(
            instance_id=self.instance.id,
            private_ip=self.instance.private_ip,
        )
