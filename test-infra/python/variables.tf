variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "layer_arn" {
  description = "ARN of the Lambda layer to test"
  type        = string
  default     = "arn:aws:lambda:us-east-1:306468203480:layer:py-3-13-anthropic-feedparser-lf:1"
}

variable "runtime" {
  description = "Lambda Python runtime version"
  type        = string
  default     = "python3.13"
}

variable "function_name" {
  description = "Name for the test Lambda function"
  type        = string
  default     = "anthropic-feedparser-test"
}
