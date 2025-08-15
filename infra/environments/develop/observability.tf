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
