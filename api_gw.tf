########################################################
# API Gateway for Manual Approval
########################################################

# API Gateway Rest API
resource "aws_api_gateway_rest_api" "approval_api" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0

  name        = format("%s-approval-api", local.name_prefix)
  description = "HTTP Endpoint for manual approval callbacks"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(
    { Name = format("%s-approval-api", local.name_prefix) },
    local.common_merged_tags
  )
}

# API Gateway Resource for /execution path
resource "aws_api_gateway_resource" "execution_resource" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.approval_api[0].id
  parent_id   = aws_api_gateway_rest_api.approval_api[0].root_resource_id
  path_part   = "execution"
}

# API Gateway Method (GET)
resource "aws_api_gateway_method" "execution_method" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0

  rest_api_id   = aws_api_gateway_rest_api.approval_api[0].id
  resource_id   = aws_api_gateway_resource.execution_resource[0].id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway Integration with Lambda
resource "aws_api_gateway_integration" "execution_integration" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.approval_api[0].id
  resource_id = aws_api_gateway_resource.execution_resource[0].id
  http_method = aws_api_gateway_method.execution_method[0].http_method

  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = module.lambda_handle_approval_callback[0].lambda_function_invoke_arn
  request_templates = {
    "application/json" = <<EOF
{
  "body": $input.json('$'),
  "headers": {
#foreach($header in $input.params().header.keySet())
    "$header": "$util.escapeJavaScript($input.params().header.get($header))"#if($foreach.hasNext),#end
#end
  },
  "method": "$context.httpMethod",
  "params": {
#foreach($param in $input.params().path.keySet())
    "$param": "$util.escapeJavaScript($input.params().path.get($param))"#if($foreach.hasNext),#end
#end
  },
  "queryStringParameters": {
#foreach($queryParam in $input.params().querystring.keySet())
    "$queryParam": "$input.params().querystring.get($queryParam)"#if($foreach.hasNext),#end
#end
  }
}
EOF
  }
}

# API Gateway Method Response
resource "aws_api_gateway_method_response" "execution_method_response" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.approval_api[0].id
  resource_id = aws_api_gateway_resource.execution_resource[0].id
  http_method = aws_api_gateway_method.execution_method[0].http_method
  status_code = "302"

  response_parameters = {
    "method.response.header.Location" = true
  }
}

# API Gateway Integration Response
resource "aws_api_gateway_integration_response" "execution_integration_response" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.approval_api[0].id
  resource_id = aws_api_gateway_resource.execution_resource[0].id
  http_method = aws_api_gateway_method.execution_method[0].http_method
  status_code = aws_api_gateway_method_response.execution_method_response[0].status_code

  response_parameters = {
    "method.response.header.Location" = "integration.response.body.headers.Location"
  }

  depends_on = [aws_api_gateway_integration.execution_integration[0]]
}

# CloudWatch Logs Role for API Gateway
resource "aws_iam_role" "api_gateway_cloudwatch_role" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0
  name  = format("%s-api-gateway-cloudwatch-role", local.name_prefix)

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    { Name = format("%s-api-gateway-cloudwatch-role", local.name_prefix) },
    local.common_merged_tags
  )
}

# CloudWatch Logs Policy for API Gateway
resource "aws_iam_role_policy" "api_gateway_cloudwatch_policy" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0
  name  = format("%s-api-gateway-cloudwatch-policy", local.name_prefix)
  role  = aws_iam_role.api_gateway_cloudwatch_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# API Gateway Account (for CloudWatch logging)
resource "aws_api_gateway_account" "approval_api_account" {
  count               = length(var.approval_email_addresses) > 0 ? 1 : 0
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_role[0].arn
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "approval_api_deployment" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0
  depends_on = [
    aws_api_gateway_method.execution_method[0],
    aws_api_gateway_integration.execution_integration[0],
    aws_api_gateway_integration_response.execution_integration_response[0],
    aws_api_gateway_resource.execution_resource[0],
  ]

  rest_api_id = aws_api_gateway_rest_api.approval_api[0].id
  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "approval_api_stage" {
  count         = length(var.approval_email_addresses) > 0 ? 1 : 0
  deployment_id = aws_api_gateway_deployment.approval_api_deployment[0].id
  rest_api_id   = aws_api_gateway_rest_api.approval_api[0].id
  stage_name    = "states"

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs[0].arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  depends_on = [
    aws_api_gateway_account.approval_api_account[0],
    aws_api_gateway_deployment.approval_api_deployment[0],
  ]

  tags = merge(
    { Name = format("%s-approval-api-stage", local.name_prefix) },
    local.common_merged_tags
  )
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  count             = length(var.approval_email_addresses) > 0 ? 1 : 0
  name              = format("/aws/apigateway/%s-approval-api", local.name_prefix)
  retention_in_days = var.log_group_retention_days
  log_group_class   = var.log_group_class

  tags = merge(
    { Name = format("%s-approval-api-logs", local.name_prefix) },
    local.common_merged_tags
  )
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway_invoke_callback" {
  count         = length(var.approval_email_addresses) > 0 ? 1 : 0
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_handle_approval_callback[0].lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.approval_api[0].execution_arn}/*"
}