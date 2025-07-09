variable "region" {
  description = "The AWS region to deploy the infrastructure to."
  type        = string
  default     = "ap-southeast-1"
}

variable "tags" {
  description = "A map of tags to apply to all resources."
  type        = map(string)
  default = {
    Project     = "redis-pubsub-101"
    Environment = "develop"
  }
}



# The Docker image tag for the webapp service.
# Using a unique tag (like a Git SHA) is recommended for production to ensure
# that `terraform apply` detects a change and triggers a new deployment.
variable "webapp_image_tag" {
  description = "Docker image tag for the webapp service."
  type        = string
  default     = "latest"
}

# The Docker image tag for the controller service.
variable "controller_image_tag" {
  description = "Docker image tag for the controller service."
  type        = string
  default     = "latest"
}

# The Docker image tag for the scheduler service.
variable "scheduler_image_tag" {
  description = "Docker image tag for the scheduler service."
  type        = string
  default     = "latest"
}
