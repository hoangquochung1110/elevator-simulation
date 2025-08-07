################################################################################
# CloudWatch Log Groups
################################################################################

resource "aws_cloudwatch_log_group" "webapp" {
  name = "/ecs/webapp"
}

resource "aws_cloudwatch_log_group" "controller" {
  name = "/ecs/controller"
}

resource "aws_cloudwatch_log_group" "scheduler" {
  name = "/ecs/scheduler"
}

################################################################################
# SSM Parameters
################################################################################

resource "aws_ssm_parameter" "adot_config" {
  name  = "/ecs/adot/config"
  type  = "String"
  value = templatefile("${path.module}/ecs-fargate-adot-config.yaml", {})
  tags  = var.tags
}
