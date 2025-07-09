################################################################################
# ECR
################################################################################

data "aws_ecr_repository" "webapp" {
  name = "${local.name}/webapp"
}

data "aws_ecr_repository" "controller" {
  name = "${local.name}/controller"
}

data "aws_ecr_repository" "scheduler" {
  name = "${local.name}/scheduler"
}


################################################################################
# ECS
################################################################################

# Logical group to contain services
data "aws_ecs_cluster" "this" {
  cluster_name = "${local.name}-cluster"
}

// this resource looks verbose as we imported it from AWS
resource "aws_ecs_service" "webapp" {
  name = "redis-pubsub-101-webapp-service"

  availability_zone_rebalancing      = "ENABLED"
  cluster                            = data.aws_ecs_cluster.this.arn
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  desired_count                      = 1
  enable_ecs_managed_tags            = true
  enable_execute_command             = false
  health_check_grace_period_seconds  = 0
  launch_type                        = "FARGATE"
  platform_version                   = "1.4.0"
  propagate_tags                     = "NONE"
  scheduling_strategy                = "REPLICA"
  tags                               = {}
  tags_all                           = {}
  task_definition                    = aws_ecs_task_definition.webapp.arn
  triggers                           = {}

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  load_balancer {
    container_name   = "webapp"
    container_port   = 8000
    elb_name         = null
    target_group_arn = aws_lb_target_group.webapp.arn
  }

  network_configuration {
    assign_public_ip = false
    security_groups = [
      aws_security_group.ecs_service_webapp_sg.id,
    ]
    subnets         = module.vpc.public_subnets
  }
}

resource "aws_ecs_service" "scheduler" {
  name            = "redis-pubsub-101-scheduler-service"
  cluster         = data.aws_ecs_cluster.this.arn
  task_definition = aws_ecs_task_definition.scheduler.arn

  desired_count    = 1
  platform_version = "1.4.0"

  # Optional: Allow external changes without Terraform plan difference
  lifecycle {
    ignore_changes = [desired_count]
  }
  launch_type = "FARGATE"

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_service_private.id]
  }
}


resource "aws_ecs_service" "controller" {
  name            = "redis-pubsub-101-controller-service"
  cluster         = data.aws_ecs_cluster.this.arn
  task_definition = aws_ecs_task_definition.controller.arn
  desired_count   = 1

  # Optional: Allow external changes without Terraform plan difference
  lifecycle {
    ignore_changes = [desired_count]
  }
  platform_version = "1.4.0"

  launch_type = "FARGATE"
  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_service_private.id]
  }
}


resource "aws_ecs_task_definition" "webapp" {
  family                   = "${local.name}-webapp"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256 # 0.25 vCPU
  memory                   = 512 # 512MB
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name      = "webapp"
    image     = "${data.aws_ecr_repository.webapp.repository_url}:${var.webapp_image_tag}"
    essential = true
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "REDIS_HOST"
        value = aws_elasticache_cluster.main.cache_nodes[0].address
      },
      {
        name  = "REDIS_PORT"
        value = tostring(aws_elasticache_cluster.main.cache_nodes[0].port)
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.restapi.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "scheduler" {
  family                   = "${local.name}-scheduler"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256 # 0.25 vCPU
  memory                   = 512 # 512MB
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name      = "scheduler"
    image     = "${data.aws_ecr_repository.scheduler.repository_url}:${var.scheduler_image_tag}"
    essential = true

    environment = [
      {
        name  = "REDIS_HOST"
        value = aws_elasticache_cluster.main.cache_nodes[0].address
      },
      {
        name  = "REDIS_PORT"
        value = tostring(aws_elasticache_cluster.main.cache_nodes[0].port)
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.scheduler.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "controller" {
  family                   = "${local.name}-controller"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256 # 0.25 vCPU
  memory                   = 512 # 512MB
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name      = "controller"
    image     = "${data.aws_ecr_repository.controller.repository_url}:${var.controller_image_tag}"
    essential = true

    environment = [
      {
        name  = "REDIS_HOST"
        value = aws_elasticache_cluster.main.cache_nodes[0].address
      },
      {
        name  = "REDIS_PORT"
        value = tostring(aws_elasticache_cluster.main.cache_nodes[0].port)
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.controller.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
}
