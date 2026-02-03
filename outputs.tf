output "notification_topic_arn" {
  description = "The ARN of the SNS topic for notifications"
  value       = aws_sns_topic.tgw_notifications.arn
}

output "send_approval_email_function_arn" {
  description = "The ARN of the send approval email Lambda function"
  value       = length(var.approval_email_addresses) > 0 ? module.lambda_send_approval_email[0].lambda_function_arn : ""
}

output "handle_approval_callback_function_arn" {
  description = "The ARN of the handle approval callback Lambda function"
  value       = length(var.approval_email_addresses) > 0 ? module.lambda_handle_approval_callback[0].lambda_function_arn : ""
}

output "handle_approval_callback_function_url" {
  description = "The URL of the handle approval callback Lambda function"
  value       = length(var.approval_email_addresses) > 0 ? aws_api_gateway_stage.approval_api_stage[0].invoke_url : ""
}

output "human_approval_email_topic_arn" {
  description = "ARN of the SNS topic for human approval emails"
  value       = length(var.approval_email_addresses) > 0 ? aws_sns_topic.human_approval_email[0].arn : ""
}

output "lambda_layer_arn" {
  description = "The ARN of the Lambda layer for shared libraries"
  value       = module.lambda_layer.lambda_layer_arn
}

output "lambda_accepter_function_arn" {
  description = "The ARN of the Lambda function that accepts TGW attachments"
  value       = module.lambda_accepter.lambda_function_arn
}

output "lambda_wait_for_available_tgwa_function_arn" {
  description = "The ARN of the Lambda function that waits for TGW attachment to be available"
  value       = module.lambda_wait_for_available_tgwa.lambda_function_arn
}

output "lambda_validate_iam_function_arn" {
  description = "The ARN of the Lambda function that validates IAM principals"
  value       = local.accept_sfn_include_iam_validation ? module.lambda_validate_iam[0].lambda_function_arn : ""
}

output "lambda_validate_ipam_function_arn" {
  description = "The ARN of the Lambda function that validates IPAM pools"
  value       = local.accept_sfn_include_ipam_validation ? module.lambda_validate_ipam[0].lambda_function_arn : ""
}

output "lambda_get_pool_tags_function_arn" {
  description = "The ARN of the Lambda function that retrieves IPAM pool tags"
  value       = local.routing_manager_sfn_include_get_pool_tags_step ? module.lambda_get_pool_tags[0].lambda_function_arn : ""
}

output "lambda_handle_association_function_arn" {
  description = "The ARN of the Lambda function that handles route table associations"
  value       = local.routing_manager_sfn_include_handle_association_step ? module.lambda_handle_association[0].lambda_function_arn : ""
}

output "lambda_handle_propagation_function_arn" {
  description = "The ARN of the Lambda function that handles route table propagations"
  value       = local.routing_manager_sfn_include_handle_propagation_step ? module.lambda_handle_propagation[0].lambda_function_arn : ""
}

output "lambda_handle_attachment_tags_function_arn" {
  description = "The ARN of the Lambda function that handles attachment tagging"
  value       = local.accept_sfn_include_attachment_tagging ? module.lambda_handle_attachment_tags[0].lambda_function_arn : ""
}

output "tgw_auto_accept_state_machine_arn" {
  description = "The ARN of the TGW auto-accept Step Function state machine"
  value       = aws_sfn_state_machine.tgw_auto_accept.arn
}

output "routing_manager_state_machine_arn" {
  description = "The ARN of the routing manager Step Function state machine"
  value       = aws_sfn_state_machine.routing_manager.arn
}

