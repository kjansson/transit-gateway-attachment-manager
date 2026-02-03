# Log group for create events
resource "aws_cloudwatch_log_group" "eventbridge_create" {
  name              = "/aws/events/${local.name_prefix}-create-log"
  retention_in_days = var.log_group_retention_days
  #kms_key_id        = module.builds.key_id
  tags = {
    Name = format("%s-create", local.name_prefix)
  }
}

# Log group for accept events
resource "aws_cloudwatch_log_group" "eventbridge_accept" {
  name              = "/aws/events/${local.name_prefix}-accept-log"
  retention_in_days = var.log_group_retention_days
  #   kms_key_id        = module.builds.key_id
  tags = merge(
  { Name = format("%s-accept", local.name_prefix) }, local.common_merged_tags)
}

#######################################################
# EventBridge for TGW attachments (create + accept)
#######################################################
module "eventbridge" {
  source  = "terraform-aws-modules/eventbridge/aws"
  version = "4.1.0"

  create_bus = false

  rules = {
    # Create rule: new TGW VPC attachments pending acceptance
    tgw_create_auto_attach = {
      description = "Trigger on CreateTransitGatewayVpcAttachment -> pendingAcceptance"
      state       = "ENABLED"
      event_pattern = jsonencode({
        source        = ["aws.ec2"]
        "detail-type" = ["AWS API Call via CloudTrail"]
        detail = {
          eventSource = ["ec2.amazonaws.com"]
          eventName   = ["CreateTransitGatewayVpcAttachment"]
          responseElements = {
            CreateTransitGatewayVpcAttachmentResponse = {
              transitGatewayVpcAttachment = {
                state = ["pendingAcceptance"]
              }
            }
          }
        }
      })
    }

    # Accept rule: attachments being accepted
    tgw_accept_auto_attach = {
      description = "Trigger on AcceptTransitGatewayVpcAttachment -> pending"
      state       = "ENABLED"
      event_pattern = jsonencode({
        source        = ["aws.ec2"]
        "detail-type" = ["AWS API Call via CloudTrail"]
        detail = {
          eventSource = ["ec2.amazonaws.com"]
          eventName   = ["AcceptTransitGatewayVpcAttachment"]
          responseElements = {
            AcceptTransitGatewayVpcAttachmentResponse = {
              transitGatewayVpcAttachment = {
                state = ["pending"]
              }
            }
          }
        }
      })
    }
  }

  targets = {
    tgw_create_auto_attach = [
      {
        name            = "TGW Accepter"
        arn             = aws_sfn_state_machine.tgw_auto_accept.arn
        attach_role_arn = true
      }
    ]

    tgw_accept_auto_attach = [
      {
        name            = "lambda_accept_auto_attach"
        arn             = aws_sfn_state_machine.routing_manager.arn
        attach_role_arn = true
      },
      {
        name = "log_accept_auto_attach"
        arn  = aws_cloudwatch_log_group.eventbridge_accept.arn
      }
    ]
  }

  create_role = true
  role_name   = format("%s-role-eventbridge", local.name_prefix)
  sfn_target_arns = [
    aws_sfn_state_machine.tgw_auto_accept.arn,
    aws_sfn_state_machine.routing_manager.arn
  ]
  attach_sfn_policy        = true
  attach_cloudwatch_policy = true
  cloudwatch_target_arns = [
    aws_cloudwatch_log_group.eventbridge_create.arn,
    "${aws_cloudwatch_log_group.eventbridge_create.arn}:*",
    "${aws_cloudwatch_log_group.eventbridge_create.arn}:*:*",
    aws_cloudwatch_log_group.eventbridge_accept.arn,
    "${aws_cloudwatch_log_group.eventbridge_accept.arn}:*",
    "${aws_cloudwatch_log_group.eventbridge_accept.arn}:*:*"
  ]

  tags = local.common_merged_tags
}