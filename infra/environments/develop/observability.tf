data "aws_cloudwatch_log_group" "webapp_logs" {
  name = "/ecs/webapp"
}

data "aws_cloudwatch_log_group" "scheduler_logs" {
  name = "/ecs/scheduler"
}

data "aws_cloudwatch_log_group" "controller_logs" {
  name = "/ecs/controller"
}

data "aws_cloudwatch_log_group" "fluentbit_logs" {
  name = "/ecs/fluentbit"
}

################################################################################
# FluentBit Configurations in SSM
################################################################################

resource "aws_ssm_parameter" "fluentbit_config_webapp" {
  name = "/ecs/fluentbit/config/webapp"
  type = "String"
  value = templatefile("${path.module}/fluentbit.conf", {
    region         = var.region
    log_group_name = data.aws_cloudwatch_log_group.webapp_logs.name
    service_name   = "webapp"
  })
  tags = var.tags
}

resource "aws_ssm_parameter" "fluentbit_config_scheduler" {
  name = "/ecs/fluentbit/config/scheduler"
  type = "String"
  value = templatefile("${path.module}/fluentbit.conf", {
    region         = var.region
    log_group_name = data.aws_cloudwatch_log_group.scheduler_logs.name
    service_name   = "scheduler"
  })
  tags = var.tags
}

resource "aws_ssm_parameter" "fluentbit_config_controller" {
  name = "/ecs/fluentbit/config/controller"
  type = "String"
  value = templatefile("${path.module}/fluentbit.conf", {
    region         = var.region
    log_group_name = data.aws_cloudwatch_log_group.controller_logs.name
    service_name   = "controller"
  })
  tags = var.tags
}
