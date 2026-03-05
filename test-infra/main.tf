terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- S3 bucket for test output ---

resource "aws_s3_bucket" "test_output" {
  bucket        = var.bucket_name
  force_destroy = true
}

# --- IAM role for Lambda ---

resource "aws_iam_role" "lambda" {
  name = "nokogiri-test-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3" {
  name = "s3-put-test-output"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:PutObject"
      Resource = "${aws_s3_bucket.test_output.arn}/*"
    }]
  })
}

# --- Lambda function ---

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_function.rb"
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_lambda_function" "nokogiri_test" {
  function_name    = "nokogiri-test"
  role             = aws_iam_role.lambda.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "ruby3.3"
  timeout          = 30
  memory_size      = 256
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  layers = [var.nokogiri_layer_arn]

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.test_output.id
    }
  }
}
