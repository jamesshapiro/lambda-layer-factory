variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "layer_arn" {
  description = "ARN of the Lambda layer to test"
  type        = string
  default     = "arn:aws:lambda:us-east-1:306468203480:layer:rb-34-nokogiri-aws-sdk-core-lf:1"
}

variable "runtime" {
  description = "Lambda Ruby runtime version"
  type        = string
  default     = "ruby3.4"
}

variable "function_name" {
  description = "Name for the test Lambda function"
  type        = string
  default     = "nokogiri-aws-sdk-test"
}
