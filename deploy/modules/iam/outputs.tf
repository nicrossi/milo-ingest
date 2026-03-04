output "execution_role_arn" {
  value = aws_iam_role.execution_role.arn
}

output "execution_role_name" {
  value = aws_iam_role.execution_role.name
}

output "ec2_instance_role_name" {
  value = aws_iam_role.execution_role.name
}

output "task_role_arn" {
  value = aws_iam_role.task_role.arn
}


