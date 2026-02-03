########################################################
# SNS Topic for TGW Auto-Accept Notifications
########################################################

resource "aws_sns_topic" "tgw_notifications" {
  name = format("%s-tgw-notifications", local.name_prefix)

  tags = merge(
    { Name = format("%s-tgw-notifications", local.name_prefix) },
    local.common_merged_tags
  )
}

resource "aws_sns_topic_policy" "tgw_notifications" {
  arn = aws_sns_topic.tgw_notifications.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.step_functions.arn
        }
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.tgw_notifications.arn
      }
    ]
  })
}

########################################################
# SNS Topic for Human Approval Emails
########################################################

resource "aws_sns_topic" "human_approval_email" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0
  name  = format("%s-human-approval-email", local.name_prefix)

  tags = merge(
    { Name = format("%s-human-approval-email", local.name_prefix) },
    local.common_merged_tags
  )
}

# SNS Topic Policy for human approval emails
resource "aws_sns_topic_policy" "human_approval_email" {
  count = length(var.approval_email_addresses) > 0 ? 1 : 0
  arn   = aws_sns_topic.human_approval_email[0].arn

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = format("%s-human-approval-email-policy", local.name_prefix)
    Statement = [
      {
        Sid    = "AllowLambdaPublish"
        Effect = "Allow"
        Principal = {
          AWS = module.lambda_send_approval_email[0].lambda_role_arn
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.human_approval_email[0].arn
      }
    ]
  })
}

# SNS Topic Subscriptions for approval emails
resource "aws_sns_topic_subscription" "human_approval_email" {
  count     = length(local.approval_email_list)
  topic_arn = aws_sns_topic.human_approval_email[0].arn
  protocol  = "email"
  endpoint  = local.approval_email_list[count.index]
}

# Local to parse comma-separated email addresses
locals {
  approval_email_list = [for email in split(",", var.approval_email_addresses) : trimspace(email) if trimspace(email) != ""]
}