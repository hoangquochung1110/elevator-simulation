
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "redis-pubsub-101"
    key    = "develop/redis-pubsub-101.ttfstate"
    region = "ap-southeast-1"
  }
}

provider "aws" {
  region = var.region
}

data "aws_availability_zones" "available" {}

################################################################################
# FluentBit Sidecar Container Definitions
################################################################################

locals {
  # FluentBit sidecar definition for webapp
  fluentbit_webapp = {
    name  = "fluentbit"
    image = "public.ecr.aws/aws-observability/aws-for-fluent-bit:2.31.12"

    environment = [
      {
        name  = "AWS_REGION"
        value = var.region
      },
      {
        name  = "SERVICE_NAME"
        value = "webapp"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.fluentbit_logs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "webapp"
      }
    }

    secrets = [
      {
        name      = "FLUENTBIT_CONFIG"
        valueFrom = aws_ssm_parameter.fluentbit_config_webapp.arn
      }
    ]

    essential = false
    cpu       = 128
    memory    = 256
  }

  # FluentBit sidecar definition for scheduler
  fluentbit_scheduler = {
    name  = "fluentbit"
    image = "public.ecr.aws/aws-observability/aws-for-fluent-bit:stable"

    environment = [
      {
        name  = "AWS_REGION"
        value = var.region
      },
      {
        name  = "SERVICE_NAME"
        value = "scheduler"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.fluentbit_logs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "scheduler"
      }
    }

    secrets = [
      {
        name      = "FLUENTBIT_CONFIG"
        valueFrom = aws_ssm_parameter.fluentbit_config_scheduler.arn
      }
    ]

    essential = false
    cpu       = 128
    memory    = 256
  }

  # FluentBit sidecar definition for controller
  fluentbit_controller = {
    name  = "fluentbit"
    image = "public.ecr.aws/aws-observability/aws-for-fluent-bit:stable"

    environment = [
      {
        name  = "AWS_REGION"
        value = var.region
      },
      {
        name  = "SERVICE_NAME"
        value = "controller"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.fluentbit_logs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "controller"
      }
    }

    secrets = [
      {
        name      = "FLUENTBIT_CONFIG"
        valueFrom = aws_ssm_parameter.fluentbit_config_controller.arn
      }
    ]

    essential = false
    cpu       = 128
    memory    = 256
  }

  # Common OTEL collector sidecar configuration
  otel_collector = {
    name      = "aws-otel-collector"
    image     = "amazon/aws-otel-collector"
    command   = ["--config", "/etc/otel/collector-config.yaml"]
    essential = true
    cpu       = 128
    memory    = 256

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "ecs/ecs-aws-otel-sidecar-collector"
        awslogs-region        = var.region
        awslogs-stream-prefix = "ecs"
        awslogs-create-group  = "true"
      }
    }

    healthCheck = {
      command     = ["/healthcheck"]
      interval    = 5
      timeout     = 6
      retries     = 5
      startPeriod = 1
    }
  }
}

locals {
  name     = "redis-pubsub-101"
  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 2)
}

################################################################################
# IAM Role for ECS Tasks
################################################################################

resource "aws_iam_role" "ecs_task_role" {
  name = "${local.name}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom policy for CloudWatch Logs
resource "aws_iam_role_policy" "fluentbit_cloudwatch_policy" {
  name = "fluentbit-cloudwatch-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })
}

# Add SSM permissions to existing execution role
resource "aws_iam_role_policy" "ssm_parameter_access" {
  name = "ssm-parameter-access"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${var.region}:*:parameter/ecs/fluentbit/config/*",
          "arn:aws:ssm:${var.region}:*:parameter/ecs/adot/config"
        ]
      }
    ]
  })
}

# Permission for ADOT Collector to publish app metrics
# and container metrics to AWS CloudWatch and sending app traces to AWS X-Ray.
resource "aws_iam_role_policy" "aws_distro_opentelemetry_policy" {
  name = "aws-distro-opentelemetry-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups",
          "logs:PutRetentionPolicy",
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries",
          "cloudwatch:PutMetricData",
          "ec2:DescribeVolumes",
          "ec2:DescribeTags",
          "ssm:GetParameters"
        ]
        Resource = "*"
      }
    ]
  })
}
################################################################################
# Security Group for ECS Services
################################################################################

resource "aws_security_group" "ecs_service_webapp_sg" {
  name        = "${local.name}-ecs-service-webapp-sg"
  description = "ECS Webapp Service Security Group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.lb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "webapp"
    },
  )
}

resource "aws_security_group" "ecs_service_private" {
  name        = "${local.name}-ecs-service-private-sg"
  description = "Security Group for containers in private subnets"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.lb.id]
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Required for ECR access
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

}

################################################################################
# CloudWatch Log Groups
################################################################################

# resource "aws_cloudwatch_log_group" "restapi" {
#   name = "/ecs/webapp"
# }

# resource "aws_cloudwatch_log_group" "controller" {
#   name = "/ecs/controller"
# }

# resource "aws_cloudwatch_log_group" "scheduler" {
#   name = "/ecs/scheduler"
# }


################################################################################
# VPC Module
################################################################################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.name}-vpc"
  cidr = local.vpc_cidr

  azs = local.azs

  enable_nat_gateway     = true
  single_nat_gateway     = false
  one_nat_gateway_per_az = true

  # Start private subnets from a different offset to avoid conflicts
  private_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 4, k + 1)]
  public_subnets  = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 4)]


  tags = var.tags
}
