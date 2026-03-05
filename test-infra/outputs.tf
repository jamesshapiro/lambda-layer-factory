output "bucket_name" {
  value = aws_s3_bucket.test_output.id
}

output "function_name" {
  value = aws_lambda_function.nokogiri_test.function_name
}

output "invoke_command" {
  description = "Sample invoke command"
  value       = "aws lambda invoke --function-name ${aws_lambda_function.nokogiri_test.function_name} --payload '{\"url\":\"https://example.com\"}' /tmp/out.json && cat /tmp/out.json"
}
