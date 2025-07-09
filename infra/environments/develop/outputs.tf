output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_arn" {
  description = "The ARN of the VPC"
  value       = module.vpc.vpc_arn
}

output "vpc_cidr_block" {
  description = "The CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "default_security_group_id" {
  description = "The ID of the security group created by default on VPC creation"
  value       = module.vpc.default_security_group_id
}

output "ecs_cluster_info" {
  value = {
    arn                 = data.aws_ecs_cluster.this.arn
    running_tasks_count = data.aws_ecs_cluster.this.running_tasks_count
  }
}

output "elasticache_cluster_info" {
  value = {
    arn                    = aws_elasticache_cluster.main.arn
    cluster_address        = aws_elasticache_cluster.main.cluster_address
    configuration_endpoint = aws_elasticache_cluster.main.configuration_endpoint
    cache_nodes            = aws_elasticache_cluster.main.cache_nodes
  }
}


output "alb_info" {
  value = {
    arn      = aws_lb.main.arn
    dns_name = aws_lb.main.dns_name
  }
}