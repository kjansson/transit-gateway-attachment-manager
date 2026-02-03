############################################################
# Lambda: common layer
############################################################

module "lambda_layer" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  create_layer = true

  layer_name          = format("%s-common", local.name_prefix)
  description         = "Common dependencies for Lambda functions"
  compatible_runtimes = ["python3.11"]

  source_path = "${path.module}/functions/src/common"
}


############################################################
# Lambda: validate_iam
############################################################
module "lambda_validate_iam" {
  count   = local.accept_sfn_include_iam_validation ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-validate-iam", local.name_prefix)
  description   = "Validate IAM principals for TGW VPC attachment creation"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/validate_iam"

  # Disable function URL (not needed for EventBridge-triggered Lambda)
  create_lambda_function_url = false

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    ALLOWED_PRINCIPAL_PATTERNS = join(",", var.allowed_principal_patterns)
    LOG_LEVEL                  = var.log_level
  }

  # No additional IAM permissions needed beyond basic Lambda execution
  attach_policy_statements = false

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-validate-iam-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: validate_ipam
############################################################
module "lambda_validate_ipam" {
  count   = local.accept_sfn_include_ipam_validation ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-validate-ipam", local.name_prefix)
  description   = "Validate VPC allocation in IPAM for TGW VPC attachment creation"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/validate_ipam"

  # Disable function URL (not needed for EventBridge-triggered Lambda)
  create_lambda_function_url = false

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    IPAM_POOL_IDS = join(",", var.ipam_pool_ids)
    LOG_LEVEL     = var.log_level
  }

  # EC2 IPAM permissions for validating VPC allocations
  attach_policy_statements = true
  policy_statements = {
    ec2_ipam_permissions = {
      effect = "Allow",
      actions = [
        "ec2:DescribeIpamPoolAllocations",
        "ec2:GetIpamPoolAllocations"
      ],
      resources = ["*"]
    }
  }

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-validate-ipam-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: accepter
############################################################
module "lambda_accepter" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-accepter", local.name_prefix)
  description   = "Accept TGW VPC attachments"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/handle_accept"

  # Disable function URL (not needed for EventBridge-triggered Lambda)
  create_lambda_function_url = false

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    LOG_LEVEL = var.log_level
  }

  # EC2 permissions for TGW operations
  attach_policy_statements = true
  policy_statements = {
    ec2_tgw_permissions = {
      effect = "Allow",
      actions = [
        "ec2:DescribeTransitGateway*",
        "ec2:AcceptTransitGatewayVpcAttachment"
      ],
      resources = ["*"]
    }
  }

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-accepter-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: wait_for_available_tgwa
############################################################
module "lambda_wait_for_available_tgwa" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-wait-for-available-tgwa", local.name_prefix)
  description   = "Wait for TGW VPC attachment to become available"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/wait_for_available_tgwa"

  # Disable function URL (not needed for EventBridge-triggered Lambda)
  create_lambda_function_url = false

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    LOG_LEVEL = var.log_level
  }

  # EC2 permissions for TGW operations
  attach_policy_statements = true
  policy_statements = {
    ec2_tgw_permissions = {
      effect = "Allow",
      actions = [
        "ec2:DescribeTransitGateway*"
      ],
      resources = ["*"]
    }
  }

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-wait-for-available-tgwa-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: get_pool_tags
############################################################
module "lambda_get_pool_tags" {
  count   = local.routing_manager_sfn_include_get_pool_tags_step ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-get-pool-tags", local.name_prefix)
  description   = "Get tags from IPAM pool"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/collect_pool_tags"

  # Disable function URL (not needed for EventBridge-triggered Lambda)
  create_lambda_function_url = false

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    IPAM_POOL_IDS            = join(",", var.ipam_pool_ids)
    LOG_LEVEL                = var.log_level
    IPAM_ASSOCIATION_TAG_KEY = var.ipam_association_tag_key
    IPAM_PROPAGATION_TAG_KEY = var.ipam_propagation_tag_key
  }

  # EC2 IPAM permissions for describing IPAM pools
  attach_policy_statements = true
  policy_statements = {
    ec2_ipam_permissions = {
      effect = "Allow",
      actions = [
        "ec2:DescribeIpamPoolAllocations",
        "ec2:GetIpamPoolAllocations",
        "ec2:DescribeIpamPools"
      ],
      resources = ["*"]
    }
  }

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-get-pool-tags-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: handle_association
############################################################
module "lambda_handle_association" {
  count   = local.routing_manager_sfn_include_handle_association_step ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-handle-association", local.name_prefix)
  description   = "Handle TGW route table associations"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/handle_association"

  # Disable function URL (not needed for EventBridge-triggered Lambda)
  create_lambda_function_url = false

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    DEFAULT_ASSOCIATE_ROUTE_TABLE_ID = var.default_associate_route_table_id
    LOG_LEVEL                        = var.log_level
  }

  # EC2 permissions for TGW association operations
  attach_policy_statements = true
  policy_statements = {
    ec2_tgw_association_permissions = {
      effect = "Allow",
      actions = [
        "ec2:DescribeTransitGateway*",
        "ec2:AssociateTransitGatewayRouteTable"
      ],
      resources = ["*"]
    }
  }

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-handle-association-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: handle_propagation
############################################################
module "lambda_handle_propagation" {
  count   = local.routing_manager_sfn_include_handle_propagation_step ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-handle-propagation", local.name_prefix)
  description   = "Handle TGW route table propagations"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/handle_propagation"

  # Disable function URL (not needed for EventBridge-triggered Lambda)
  create_lambda_function_url = false

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    DEFAULT_PROPAGATE_ROUTE_TABLE_IDS = var.default_propagate_route_table_ids
    LOG_LEVEL                         = var.log_level
  }

  # EC2 permissions for TGW propagation operations
  attach_policy_statements = true
  policy_statements = {
    ec2_tgw_propagation_permissions = {
      effect = "Allow",
      actions = [
        "ec2:DescribeTransitGateway*",
        "ec2:EnableTransitGatewayRouteTablePropagation"
      ],
      resources = ["*"]
    }
  }

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-handle-propagation-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: handle_attachment_tags
############################################################
module "lambda_handle_attachment_tags" {
  count         = local.accept_sfn_include_attachment_tagging ? 1 : 0
  source        = "terraform-aws-modules/lambda/aws"
  version       = "8.1.0"
  function_name = format("%s-handle-attachment-tags", local.name_prefix)
  description   = "Handle TGW attachment tags"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true
  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/handle_attachment_tags"
  # Disable function URL (not needed for EventBridge-triggered Lambda)
  create_lambda_function_url = false
  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class
  environment_variables = {
    ATTACHMENT_TAG_KEY   = var.attachment_tag_key
    ATTACHMENT_TAG_VALUE = var.attachment_tag_value
    LOG_LEVEL            = var.log_level
  }
  # EC2 permissions for TGW operations
  attach_policy_statements = true
  policy_statements = {
    ec2_tgw_describe_permissions = {
      effect = "Allow",
      actions = [
        "ec2:DescribeTransitGateway*",
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      resources = ["*"]
    }
  }
  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]
  tags = merge(
    { Name = format("%s-handle-attachment-tags-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: send_approval_email
############################################################
module "lambda_send_approval_email" {
  count   = local.accept_sfn_include_manual_approval ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-send-approval-email", local.name_prefix)
  description   = "Generate approval email content for Step Functions human approval task"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/send_approval_email"

  # Disable function URL (not needed for Step Functions)
  create_lambda_function_url = false

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    SNS_TOPIC_ARN = aws_sns_topic.human_approval_email[0].arn
    LOG_LEVEL     = var.log_level
  }

  # SNS permissions for publishing approval emails
  attach_policy_statements = true
  policy_statements = {
    sns_publish_permissions = {
      effect = "Allow",
      actions = [
        "sns:Publish"
      ],
      resources = [aws_sns_topic.tgw_notifications.arn]
    }
  }

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-send-approval-email-function", local.name_prefix) },
    local.common_merged_tags
  )
}

############################################################
# Lambda: handle_approval_callback
############################################################
module "lambda_handle_approval_callback" {
  count   = local.accept_sfn_include_manual_approval ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.1.0"

  function_name = format("%s-handle-approval-callback", local.name_prefix)
  description   = "Handle approval/rejection callbacks from API Gateway to Step Functions"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.function_timeout
  memory_size   = var.function_memory_size
  publish       = true

  # Use source path for automatic ZIP creation
  source_path = "${path.module}/functions/src/handle_approval_callback"

  # Enable function URL for API Gateway integration
  create_lambda_function_url = true
  cors = {
    allow_credentials = false
    allow_headers     = ["date", "keep-alive"]
    allow_methods     = ["GET"]
    allow_origins     = ["*"]
    expose_headers    = ["date", "keep-alive"]
    max_age           = 86400
  }

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = var.log_group_retention_days
  cloudwatch_logs_log_group_class   = var.log_group_class

  environment_variables = {
    EMAIL_ADDRESSES = var.approval_email_addresses
    LOG_LEVEL       = var.log_level
  }

  # Step Functions permissions for sending task success
  attach_policy_statements = true
  policy_statements = {
    stepfunctions_permissions = {
      effect = "Allow",
      actions = [
        "states:SendTaskSuccess",
        "states:SendTaskFailure"
      ],
      resources = ["*"]
    }
  }

  # Include common layer
  layers = [module.lambda_layer.lambda_layer_arn]

  tags = merge(
    { Name = format("%s-handle-approval-callback-function", local.name_prefix) },
    local.common_merged_tags
  )
}