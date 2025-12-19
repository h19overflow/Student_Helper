# Networking Component Documentation

This directory contains the networking infrastructure definitions for the Student Helper application.

## VPC Architecture Diagram

```mermaid
graph TB
    subgraph VPC ["VPC (10.0.0.0/16)"]

        %% Components
        IGW[Internet Gateway]

        subgraph Public_Zone ["Public Zone (AZ-0)"]
            PublicSubnet[("Public Subnet<br>10.0.0.0/24")]
            PublicRT[[Public Route Table]]
        end

        subgraph Private_Zone ["Private Zone (Isolated)"]
            direction TB
            BackendSubnet[("Private Subnet (EC2)<br>10.0.1.0/24")]
            LambdaSubnet[("Lambda Subnet<br>10.0.2.0/24")]

            subgraph Data_Layer ["Data Layer (RDS)"]
                DataSubnetA[("Data Subnet A (AZ-0)<br>10.0.3.0/24")]
                DataSubnetB[("Data Subnet B (AZ-1)<br>10.0.4.0/24")]
            end

            PrivateRT[[Private Route Table]]
        end

        %% Routing Relationships
        PublicSubnet --- PublicRT
        PublicRT -- "0.0.0.0/0" --> IGW
        IGW --> Internet((Internet))

        BackendSubnet --- PrivateRT
        LambdaSubnet --- PrivateRT
        DataSubnetA --- PrivateRT
        DataSubnetB --- PrivateRT

        %% Implicit Local Route Explanation
        PrivateRT -. "10.0.0.0/16 (Local)" .-> BackendSubnet
        PrivateRT -. "10.0.0.0/16 (Local)" .-> LambdaSubnet
        PrivateRT -. "10.0.0.0/16 (Local)" .-> DataSubnetA

        %% Traffic Flow Examples
        EC2[EC2 Backend] -.->|Internal Traffic| RDS[RDS Database]
        linkStyle 8,9,10 stroke-width:2px,fill:none,stroke:green,stroke-dasharray: 5 5;
    end

    classDef subnet fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000000,font-weight:bold;
    classDef rt fill:#fff3e0,stroke:#ff6f00,stroke-width:2px,shape:rect,color:#000000,font-weight:bold;
    classDef igw fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,shape:hexagon,color:#000000,font-weight:bold;

    class PublicSubnet,BackendSubnet,LambdaSubnet,DataSubnetA,DataSubnetB subnet;
    class PublicRT,PrivateRT rt;
    class IGW igw;
```

## Key Components

1.  **VPC**: The isolated network container.
2.  **Internet Gateway (IGW)**: The exit point for public traffic.
3.  **Route Tables**:
    - **Public**: Directs traffic to IGW (0.0.0.0/0).
    - **Private**: No internet access. Uses implicit local route (10.0.0.0/16) for internal communication.
4.  **Subnets**:
    - **Public**: For NAT Gateway (if needed) or public resources.
    - **Private/Lambda/Data**: Isolated subnets for application logic and storage.
