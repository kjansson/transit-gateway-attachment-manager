locals {
  account_id = data.aws_caller_identity.current.account_id
  # Get the name prefix
  name_prefix = format("%s-%s", var.environment, var.name_prefix)
  # Merge common tags with additional tags if any
  common_merged_tags = merge(
    {
      environment = var.environment
    },
    var.additional_tags
  )

  ##################################
  # Accept attachment state machine
  ##################################

  # Merge validation steps based on configuration
  accept_sfn_conditional_validation_steps = merge(
    local.accept_sfn_include_iam_validation ? local.accept_sfn_check_iam_step : {},
    local.accept_sfn_include_ipam_validation ? local.accept_sfn_check_ipam_step : {},
    local.accept_sfn_include_manual_approval ? local.accept_sfn_manual_approval_step : null
  )

  # Merge acceptance steps based on configuration
  accept_sfn_conditional_acceptance_steps = merge(
    local.accept_sfn_accept_step,
    local.accept_sfn_include_attachment_tagging ? local.accept_sfn_tag_attachment_step : {},
    local.accept_sfn_tag_publish_success_step,
    local.accept_sfn_tag_publish_failure_step,
    local.accept_sfn_failure_step,
  )

  # Merge all steps that should be included
  accept_sfn_all_steps = merge(
    local.accept_sfn_conditional_validation_steps,
    local.accept_sfn_conditional_acceptance_steps
  )

  # Determine the start step based on configuration
  accept_sfn_start_step = coalesce(
    length(var.allowed_principal_patterns) > 0 ? "Check IAM principal" : null,
    length(var.ipam_pool_ids) > 0 ? "Check IPAM pool" : null,
    length(var.approval_email_addresses) > 0 ? "Manual Approval" : "Accept attachment",
    "Accept attachment"
  )

  # Determine if specific steps should be included based on configuration
  accept_sfn_include_manual_approval    = length(var.approval_email_addresses) > 0 ? true : false
  accept_sfn_include_iam_validation     = length(var.allowed_principal_patterns) > 0 ? true : false
  accept_sfn_include_ipam_validation    = length(var.ipam_pool_ids) > 0 ? true : false
  accept_sfn_include_attachment_tagging = var.attachment_tag_key != "" && var.attachment_tag_value != "" ? true : false
  accept_sfn_manual_approval_step = {
    "Manual Approval" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke.waitForTaskToken",
      "Arguments" : {
        "FunctionName" : local.accept_sfn_include_manual_approval ? "${module.lambda_send_approval_email[0].lambda_function_arn}:$LATEST" : "",
        "Payload" : local.accept_sfn_include_manual_approval ? "{% $merge([$states.input, {'ExecutionContext': $states.context, 'APIGatewayEndpoint': 'https://${aws_api_gateway_rest_api.approval_api[0].id}.execute-api.${data.aws_region.current.region}.amazonaws.com/states'}]) %}" : ""
      },
      "Output" : "{% $merge([$states.input, {'GetManualApprovalEventPayload': $states.result}]) %}",
      "Catch" : [
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure"
        }
      ],
      "Next" : "Manual Approval Choice"
    },
    "Manual Approval Choice" : {
      "Type" : "Choice",
      "Choices" : [
        {
          "Condition" : "{% $contains($states.input.GetManualApprovalEventPayload.Status, /^Approved!/) %}",
          "Next" : "Accept attachment"
        },
        {
          "Condition" : "{% $contains($states.input.GetManualApprovalEventPayload.Status, /^Rejected!/) %}",
          "Next" : "Publish failure"
        }
      ],
      "Default" : "Publish failure"
    },
  }

  accept_sfn_accept_sfn_check_iam_step_next = coalesce(
    length(var.ipam_pool_ids) > 0 ? "Check IPAM pool" : null,
    length(var.approval_email_addresses) > 0 ? "Manual Approval" : "Accept attachment",
    "Accept attachment"
  )
  accept_sfn_check_iam_step = {
    "Check IAM principal" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke",
      "Arguments" : {
        "FunctionName" : local.accept_sfn_include_iam_validation ? "${module.lambda_validate_iam[0].lambda_function_arn}:$LATEST" : "",
        "Payload" : "{% $states.input %}"
      },
      "Output" : "{% $merge([$states.input, {'IAMValidationPayload': $states.result}]) %}",
      "Catch" : [
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure"
        }
      ],
      "Retry" : [
        {
          "ErrorEquals" : [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds" : 1,
          "MaxAttempts" : 3,
          "BackoffRate" : 2,
          "JitterStrategy" : "FULL"
        }
      ],
      "Next" : local.accept_sfn_accept_sfn_check_iam_step_next
    },
  }
  accept_sfn_check_ipam_step = {
    "Check IPAM pool" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke",
      "Arguments" : {
        "FunctionName" : length(var.ipam_pool_ids) > 0 ? "${module.lambda_validate_ipam[0].lambda_function_arn}:$LATEST" : "",
        "Payload" : "{% $states.input %}"
      },
      "Output" : "{% $merge([$states.input, {'IPAMValidationPayload': $states.result}]) %}",
      "Catch" : [
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure"
        }
      ],
      "Retry" : [
        {
          "ErrorEquals" : [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds" : 1,
          "MaxAttempts" : 3,
          "BackoffRate" : 2,
          "JitterStrategy" : "FULL"
        }
      ],
      "Next" : length(var.approval_email_addresses) > 0 ? "Manual Approval" : "Accept attachment"
    },
  }

  accept_sfn_tag_attachment_step = {
    "Tag attachment" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke",
      "Arguments" : {
        "FunctionName" : local.accept_sfn_include_attachment_tagging ? "${module.lambda_handle_attachment_tags[0].lambda_function_arn}:$LATEST" : "",
        "Payload" : "{% $states.input %}"
      },
      "Output" : "{% $merge([$states.input, {'TagAttachmentPayload': $states.result}]) %}",
      "Catch" : [

        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure"
        }
      ],
      "Retry" : [
        {
          "ErrorEquals" : [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds" : 1,
          "MaxAttempts" : 3,
          "BackoffRate" : 2,
          "JitterStrategy" : "FULL"
        }
      ],
      "Next" : "Publish success"
    },
  }

  accept_sfn_tag_publish_success_step = {
    "Publish success" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::sns:publish",
      "Arguments" : {
        "TopicArn" : "${aws_sns_topic.tgw_notifications.arn}",
        "Message" : {
          "message" : "Success"
        }
      },
      "End" : true
    },
  }

  accept_sfn_tag_publish_failure_step = {
    "Publish failure" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::sns:publish",
      "Arguments" : {
        "TopicArn" : "${aws_sns_topic.tgw_notifications.arn}",
        "Message" : {
          "message" : "Failure"
        }
      },
      "Next" : "Fail"
    },
  }

  accept_sfn_accept_step = {
    "Accept attachment" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke",
      "Arguments" : {
        "FunctionName" : "${module.lambda_accepter.lambda_function_arn}:$LATEST",
        "Payload" : "{% $states.input %}"
      },
      "Output" : "{% $merge([$states.input, {'AcceptAttachmentPayload': $states.result}]) %}",
      "Catch" : [
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure"
        }
      ],
      "Retry" : [
        {
          "ErrorEquals" : [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds" : 1,
          "MaxAttempts" : 3,
          "BackoffRate" : 2,
          "JitterStrategy" : "FULL"
        }
      ],
      "Next" : local.accept_sfn_include_attachment_tagging ? "Tag attachment" : "Publish success"
    },
  }

  accept_sfn_failure_step = {
    "Fail" : {
      "Type" : "Fail",
      "Cause" : "TGW Auto-Accept workflow failed",
      "Error" : "WorkflowFailed"
    }
  }


  ####################################
  # Routing manager state machine
  ####################################

  # Merge initial steps based on configuration
  routing_manager_sfn_core_steps = merge(
    local.routing_manager_sfn_wait_for_available_step,
    local.routing_manager_sfn_include_get_pool_tags_step ? local.routing_manager_sfn_get_pool_tags_step : {}
  )

  # Merge processing steps based on configuration
  routing_manager_sfn_processing_steps = merge(
    local.routing_manager_sfn_include_handle_association_step ? local.routing_manager_sfn_handle_association_step : {},
    local.routing_manager_sfn_include_handle_propagation_step ? local.routing_manager_sfn_handle_propagation_step : {}
  )

  # Merge all steps that should be included
  routing_manager_sfn_all_steps = merge(
    local.routing_manager_sfn_core_steps,
    local.routing_manager_sfn_processing_steps,
    local.routing_manager_sfn_notification_steps
  )

  # Determine if specific steps should be included based on configuration
  routing_manager_sfn_include_get_pool_tags_step      = var.ipam_association_tag_key != "" || var.ipam_propagation_tag_key != "" ? true : false
  routing_manager_sfn_include_handle_association_step = var.ipam_association_tag_key != "" || var.default_associate_route_table_id != "" ? true : false
  routing_manager_sfn_include_handle_propagation_step = var.ipam_propagation_tag_key != "" || var.default_propagate_route_table_ids != "" ? true : false

  routing_manager_sfn_start_step = "Wait for attachment available"
  routing_manager_sfn_wait_for_available_step = {
    "Wait for attachment available" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke",
      "Arguments" : {
        "FunctionName" : "${module.lambda_wait_for_available_tgwa.lambda_function_arn}:$LATEST",
        "Payload" : "{% $states.input %}"
      },
      "Output" : "{% $merge([$states.input, {'WaitForAvailablePayload': $states.result}]) %}",
      "Catch" : [
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure"
        }
      ],
      "Retry" : [
        {
          "ErrorEquals" : [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds" : 1,
          "MaxAttempts" : 3,
          "BackoffRate" : 2,
          "JitterStrategy" : "FULL"
        },
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "IntervalSeconds" : 10,
          "MaxAttempts" : 30,
          "BackoffRate" : 1.2,
          "JitterStrategy" : "FULL"
        }
      ],
      "Next" : local.routing_manager_sfn_include_get_pool_tags_step ? "Get pool tags" : local.routing_manager_sfn_include_handle_association_step ? "Handle association" : local.routing_manager_sfn_include_handle_propagation_step ? "Handle propagation" : "Publish success"
    }
  }

  routing_manager_sfn_get_pool_tags_step = {
    "Get pool tags" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke",
      "Arguments" : {
        "FunctionName" : local.routing_manager_sfn_include_get_pool_tags_step ? "${module.lambda_get_pool_tags[0].lambda_function_arn}:$LATEST" : "",
        "Payload" : "{% $states.input %}"
      },
      "Output" : "{% $merge([$states.input, {'GetPoolTagsPayload': $states.result}]) %}",
      "Catch" : [
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure"
        }
      ],
      "Retry" : [
        {
          "ErrorEquals" : [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds" : 1,
          "MaxAttempts" : 3,
          "BackoffRate" : 2,
          "JitterStrategy" : "FULL"
        }
      ],
      "Next" : local.routing_manager_sfn_include_handle_association_step ? "Handle association" : local.routing_manager_sfn_include_handle_propagation_step ? "Handle propagation" : "Publish success"
    }
  }
  routing_manager_sfn_handle_association_step = {
    "Handle association" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke",
      "Arguments" : {
        "FunctionName" : local.routing_manager_sfn_include_handle_association_step ? "${module.lambda_handle_association[0].lambda_function_arn}:$LATEST" : "",
        "Payload" : "{% $states.input %}"
      },
      "Output" : "{% $merge([$states.input, {'HandleAssociationPayload': $states.result}]) %}",
      "Catch" : [
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure",
          "Output" : "{% $merge([$states.input, {'HandleAssociationPayload': $states.errorOutput}]) %}"
        }
      ],
      "Retry" : [
        {
          "ErrorEquals" : [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds" : 1,
          "MaxAttempts" : 3,
          "BackoffRate" : 2,
          "JitterStrategy" : "FULL"
        }
      ],
      "Next" : local.routing_manager_sfn_include_handle_propagation_step ? "Handle propagation" : "Publish success"
    }
  }

  routing_manager_sfn_handle_propagation_step = {
    "Handle propagation" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::lambda:invoke",
      "Arguments" : {
        "FunctionName" : local.routing_manager_sfn_include_handle_propagation_step ? "${module.lambda_handle_propagation[0].lambda_function_arn}:$LATEST" : "",
        "Payload" : "{% $states.input %}"
      },
      "Output" : "{% $merge([$states.input, {'HandlePropagationPayload': $states.result}]) %}",
      "Catch" : [
        {
          "ErrorEquals" : [
            "States.TaskFailed"
          ],
          "Next" : "Publish failure",
          "Output" : "{% $merge([$states.input, {'HandlePropagationPayload': $states.errorOutput}]) %}"
        }
      ],
      "Retry" : [
        {
          "ErrorEquals" : [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds" : 1,
          "MaxAttempts" : 3,
          "BackoffRate" : 2,
          "JitterStrategy" : "FULL"
        }
      ],
      "Next" : "Publish success"
    }
  }

  routing_manager_sfn_notification_steps = {
    "Publish success" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::sns:publish",
      "Arguments" : {
        "TopicArn" : "${aws_sns_topic.tgw_notifications.arn}",
        "Message" : {
          "message" : "Routing Manager - Success"
        }
      },
      "End" : true
    },
    "Publish failure" : {
      "Type" : "Task",
      "Resource" : "arn:aws:states:::sns:publish",
      "Arguments" : {
        "TopicArn" : "${aws_sns_topic.tgw_notifications.arn}",
        "Message" : {
          "message" : "Routing Manager - Failed"
        }
      },
      "Next" : "Fail"
    },
    "Fail" : {
      "Type" : "Fail",
      "Cause" : "Routing Manager workflow failed",
      "Error" : "WorkflowFailed"
    }
  }
}

