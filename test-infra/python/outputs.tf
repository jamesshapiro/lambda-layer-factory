output "function_name" {
  value = aws_lambda_function.test.function_name
}

output "invoke_command" {
  description = "Sample invoke command"
  value       = "aws lambda invoke --function-name ${aws_lambda_function.test.function_name} --payload '{}' /tmp/out.json && cat /tmp/out.json"
}
