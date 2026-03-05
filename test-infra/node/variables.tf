variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "layer_arn" {
  description = "ARN of the Lambda layer to test"
  type        = string
}

variable "runtime" {
  description = "Lambda Node.js runtime version"
  type        = string
  default     = "nodejs22.x"
}

variable "function_name" {
  description = "Name for the test Lambda function"
  type        = string
  default     = "lodash-axios-test"
}
