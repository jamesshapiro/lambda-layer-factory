variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "nokogiri_layer_arn" {
  description = "ARN of the Nokogiri Lambda layer"
  type        = string
  default     = "arn:aws:lambda:us-east-1:306468203480:layer:rb-33-nokogiri-lf:1"
}

variable "bucket_name" {
  description = "S3 bucket for test output"
  type        = string
  default     = "nokogiri-test-output"
}
