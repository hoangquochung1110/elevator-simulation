resource "aws_cloudwatch_log_group" "webapp_logs" {
  name              = "/ecs/webapp"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "scheduler_logs" {
  name              = "/ecs/scheduler"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "controller_logs" {
  name              = "/ecs/controller"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "fluentbit_logs" {
  name              = "/ecs/fluentbit"
  retention_in_days = 7
  tags              = var.tags
}

################################################################################
# FluentBit Configurations in SSM
################################################################################

resource "aws_ssm_parameter" "fluentbit_config_webapp" {
  name = "/ecs/fluentbit/config/webapp"
  type = "String"
  value = templatefile("${path.module}/fluentbit.conf", {
    region         = var.region
    log_group_name = aws_cloudwatch_log_group.webapp_logs.name
    service_name   = "webapp"
  })
  tags = var.tags
}

resource "aws_ssm_parameter" "fluentbit_config_scheduler" {
  name = "/ecs/fluentbit/config/scheduler"
  type = "String"
  value = templatefile("${path.module}/fluentbit.conf", {
    region         = var.region
    log_group_name = aws_cloudwatch_log_group.scheduler_logs.name
    service_name   = "scheduler"
  })
  tags = var.tags
}

resource "aws_ssm_parameter" "fluentbit_config_controller" {
  name = "/ecs/fluentbit/config/controller"
  type = "String"
  value = templatefile("${path.module}/fluentbit.conf", {
    region         = var.region
    log_group_name = aws_cloudwatch_log_group.controller_logs.name
    service_name   = "controller"
  })
  tags = var.tags
}

resource "aws_ssm_parameter" "adot_config" {
  name  = "/ecs/adot/config"
  type  = "String"
  value = templatefile("${path.module}/ecs-fargate-adot-config.yaml", {})
  tags  = var.tags
}
