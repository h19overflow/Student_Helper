"""
RDS PostgreSQL Component for Relational Database.

Access Control - Who Can Connect:
1. EC2 Backend (backend_sg) → Port 5432 ✅
2. Lambda Processor (lambda_sg) → Port 5432 ✅
3. Anyone else → DENIED ❌

How the Connection Works:
1. Routing: EC2/Lambda in private subnets use the implicit LOCAL route (10.0.0.0/16) to reach RDS in the data subnet. Traffic never leaves the VPC.
2. Security Group: database_sg only allows ingress on port 5432 from backend_sg and lambda_sg (identity-based, not IP-based).
3. Credentials: manage_master_user_password=True means AWS auto-generates the password and stores it in Secrets Manager. EC2/Lambda retrieve it at runtime via VPC Endpoints.

Result: Zero public exposure. No internet path. Only trusted identities (SGs) can connect.
"""

from dataclasses import dataclass

import pulumi
import pulumi_aws as aws

from IAC.utils.tags import create_tags
from IAC.configs.base import EnvironmentConfig


@dataclass
class RdsOutputs:
    """Output values from RDS component."""
    endpoint: pulumi.Output[str]
    port: pulumi.Output[int]
    database_name: pulumi.Output[str]


class RdsPostgresComponent(pulumi.ComponentResource):
    """
    RDS PostgreSQL database for application persistence.

    Stores sessions, jobs, document metadata, and chat history.
    """

    def __init__(
        self,
        name: str,
        environment: str,
        config: EnvironmentConfig,
        subnet_ids: list[pulumi.Input[str]],
        security_group_id: pulumi.Input[str],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("custom:storage:RdsPostgres", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)
        db_name = "studenthelper"

        # DB Subnet Group
        self.subnet_group = aws.rds.SubnetGroup(
            f"{name}-subnet-group",
            subnet_ids=subnet_ids,
            tags=create_tags(environment, f"{name}-subnet-group"),
            opts=child_opts,
        )

        # Parameter Group
        self.parameter_group = aws.rds.ParameterGroup(
            f"{name}-params",
            family="postgres16",
            parameters=[
                aws.rds.ParameterGroupParameterArgs(
                    name="log_statement",
                    value="all",
                ),
                aws.rds.ParameterGroupParameterArgs(
                    name="log_min_duration_statement",
                    value="1000",  # Log queries > 1 second
                ),
            ],
            tags=create_tags(environment, f"{name}-params"),
            opts=child_opts,
        )

        # RDS Instance
        self.instance = aws.rds.Instance(
            f"{name}-postgres",
            identifier=f"{name}-postgres",
            engine="postgres",
            engine_version="16",
            instance_class=config.rds_instance_class,
            allocated_storage=config.rds_allocated_storage,
            storage_type="gp3",
            storage_encrypted=True,
            db_name=db_name,
            username="postgres",
            manage_master_user_password=True,  # AWS manages password in Secrets Manager
            db_subnet_group_name=self.subnet_group.name,
            vpc_security_group_ids=[security_group_id],
            parameter_group_name=self.parameter_group.name,
            multi_az=config.multi_az,
            deletion_protection=config.enable_deletion_protection,
            skip_final_snapshot=not config.is_production,
            final_snapshot_identifier=f"{name}-final-snapshot" if config.is_production else None,
            backup_retention_period=7 if config.is_production else 1,
            backup_window="03:00-04:00",
            maintenance_window="Mon:04:00-Mon:05:00",
            tags=create_tags(environment, f"{name}-postgres"),
            opts=child_opts,
        )

        self.register_outputs({
            "endpoint": self.instance.endpoint,
            "port": self.instance.port,
            "database_name": db_name,
        })

    def get_outputs(self) -> RdsOutputs:
        """Get RDS output values."""
        return RdsOutputs(
            endpoint=self.instance.endpoint,
            port=self.instance.port,
            database_name=pulumi.Output.from_input("studenthelper"),
        )
