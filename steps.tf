########################################################
# Step Functions IAM Role
########################################################

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions" {
  name = format("%s-step-functions-role", local.name_prefix)

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    { Name = format("%s-step-functions-role", local.name_prefix) },
    local.common_merged_tags
  )
}

# IAM Policy for Lambda invocation permissions
resource "aws_iam_policy" "step_functions_lambda" {
  name        = format("%s-step-functions-lambda-policy", local.name_prefix)
  description = "Allows Step Functions to invoke Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = compact([
          length(var.allowed_principal_patterns) > 0 ? "${module.lambda_validate_iam[0].lambda_function_arn}:*" : null,
          length(var.ipam_pool_ids) > 0 ? "${module.lambda_validate_ipam[0].lambda_function_arn}:*" : null,
          "${module.lambda_accepter.lambda_function_arn}:*",
          var.attachment_tag_key != "" && var.attachment_tag_value != "" ? "${module.lambda_handle_attachment_tags[0].lambda_function_arn}:*" : null,
          length(var.approval_email_addresses) > 0 ? "${module.lambda_send_approval_email[0].lambda_function_arn}:*" : null,
          length(var.approval_email_addresses) > 0 ? "${module.lambda_handle_approval_callback[0].lambda_function_arn}:*" : null
        ])
      }
    ]
  })

  tags = merge(
    { Name = format("%s-step-functions-lambda-policy", local.name_prefix) },
    local.common_merged_tags
  )
}

# IAM Policy for SSM parameter access
resource "aws_iam_policy" "step_functions_ssm" {
  name        = format("%s-step-functions-ssm-policy", local.name_prefix)
  description = "Allows Step Functions to access SSM parameters"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.name_prefix}/*"
        ]
      }
    ]
  })

  tags = merge(
    { Name = format("%s-step-functions-ssm-policy", local.name_prefix) },
    local.common_merged_tags
  )
}

# IAM Policy for SNS publish permissions
resource "aws_iam_policy" "step_functions_sns" {
  name        = format("%s-step-functions-sns-policy", local.name_prefix)
  description = "Allows Step Functions to publish to SNS topics"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.tgw_notifications.arn
        ]
      }
    ]
  })

  tags = merge(
    { Name = format("%s-step-functions-sns-policy", local.name_prefix) },
    local.common_merged_tags
  )
}

# Attach Lambda policy to role
resource "aws_iam_role_policy_attachment" "step_functions_lambda" {
  role       = aws_iam_role.step_functions.name
  policy_arn = aws_iam_policy.step_functions_lambda.arn
}

# Attach SSM policy to role
resource "aws_iam_role_policy_attachment" "step_functions_ssm" {
  role       = aws_iam_role.step_functions.name
  policy_arn = aws_iam_policy.step_functions_ssm.arn
}

# Attach SNS policy to role
resource "aws_iam_role_policy_attachment" "step_functions_sns" {
  role       = aws_iam_role.step_functions.name
  policy_arn = aws_iam_policy.step_functions_sns.arn
}

########################################################
# Step Functions State Machine
########################################################

resource "aws_sfn_state_machine" "tgw_auto_accept" {
  name     = format("%s-tgw-auto-accept", local.name_prefix)
  role_arn = aws_iam_role.step_functions.arn
  type     = "STANDARD"

  definition = jsonencode({
    "Comment" : "Transit Gateway Attachment validation and auto-accept",
    "StartAt" : local.accept_sfn_start_step,
    "States" : local.accept_sfn_all_steps,
    "QueryLanguage" : "JSONata"
  })

  tags = merge(
    { Name = format("%s-tgw-auto-accept", local.name_prefix) },
    local.common_merged_tags
  )
}

########################################################
# Routing Manager Step Functions IAM Role
########################################################

# IAM Role for Routing Manager Step Functions
resource "aws_iam_role" "routing_manager_step_functions" {
  name = format("%s-routing-manager-step-functions-role", local.name_prefix)

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    { Name = format("%s-routing-manager-step-functions-role", local.name_prefix) },
    local.common_merged_tags
  )
}

# IAM Policy for Lambda invocation permissions (accepter lambda)
resource "aws_iam_policy" "routing_manager_lambda" {
  name        = format("%s-routing-manager-lambda-policy", local.name_prefix)
  description = "Allows Routing Manager Step Functions to invoke accepter Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = compact([
          "${module.lambda_wait_for_available_tgwa.lambda_function_arn}:*",
          local.routing_manager_sfn_include_get_pool_tags_step ? "${module.lambda_get_pool_tags[0].lambda_function_arn}:*" : null,
          local.routing_manager_sfn_include_handle_association_step ? "${module.lambda_handle_association[0].lambda_function_arn}:*" : null,
          local.routing_manager_sfn_include_handle_propagation_step ? "${module.lambda_handle_propagation[0].lambda_function_arn}:*" : null,
        ])
      }
    ]
  })

  tags = merge(
    { Name = format("%s-routing-manager-lambda-policy", local.name_prefix) },
    local.common_merged_tags
  )
}

# IAM Policy for SNS publish permissions
resource "aws_iam_policy" "routing_manager_sns" {
  name        = format("%s-routing-manager-sns-policy", local.name_prefix)
  description = "Allows Routing Manager Step Functions to publish to SNS topics"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.tgw_notifications.arn
        ]
      }
    ]
  })

  tags = merge(
    { Name = format("%s-routing-manager-sns-policy", local.name_prefix) },
    local.common_merged_tags
  )
}

# Attach Lambda policy to routing manager role
resource "aws_iam_role_policy_attachment" "routing_manager_lambda" {
  role       = aws_iam_role.routing_manager_step_functions.name
  policy_arn = aws_iam_policy.routing_manager_lambda.arn
}

# Attach SNS policy to routing manager role
resource "aws_iam_role_policy_attachment" "routing_manager_sns" {
  role       = aws_iam_role.routing_manager_step_functions.name
  policy_arn = aws_iam_policy.routing_manager_sns.arn
}

########################################################
# Routing Manager Step Functions State Machine
########################################################

resource "aws_sfn_state_machine" "routing_manager" {
  name     = format("%s-routing-manager", local.name_prefix)
  role_arn = aws_iam_role.routing_manager_step_functions.arn
  type     = "STANDARD"

  definition = jsonencode({
    "Comment" : "Routing Manager - Manage TGW route table associations and propagations",
    "StartAt" : local.routing_manager_sfn_start_step,
    "States" : local.routing_manager_sfn_all_steps,
    "QueryLanguage" : "JSONata"
  })

  tags = merge(
    { Name = format("%s-routing-manager", local.name_prefix) },
    local.common_merged_tags
  )
}