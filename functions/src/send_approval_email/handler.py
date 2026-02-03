import os
import logging
from urllib.parse import quote
from typing import Dict, Any
from urllib.parse import quote_plus
import boto3
from botocore.exceptions import ClientError

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

# Environment variables
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to generate approval email content for Step Functions human approval task.
    
    This function extracts execution context and API Gateway endpoint from the event,
    then constructs approve/reject URLs and email message content.
    
    Args:
        event: Step Functions event containing ExecutionContext and APIGatewayEndpoint
        context: Lambda context object
        
    Returns:
        Dict containing the email message, subject, and approval URLs
    """
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')
    
    try:
        # Extract execution context
        execution_context = event.get('ExecutionContext')
        if not execution_context:
            raise ValueError("ExecutionContext not found in event")
        
        logger.debug(f'executionContext: {execution_context}')
        
        # Extract execution details
        execution = execution_context.get('Execution', {})
        execution_name = execution.get('Name')
        if not execution_name:
            raise ValueError("Execution name not found in ExecutionContext")
        
        logger.debug(f'executionName: {execution_name}')
        
        # Extract state machine details
        state_machine = execution_context.get('StateMachine', {})
        state_machine_name = state_machine.get('Name')
        if not state_machine_name:
            raise ValueError("StateMachine name not found in ExecutionContext")
        
        logger.debug(f'statemachineName: {state_machine_name}')
        
        # Extract task token
        task = execution_context.get('Task', {})
        task_token = task.get('Token')
        if not task_token:
            raise ValueError("Task token not found in ExecutionContext")
        
        logger.debug(f'taskToken: {task_token}')
        
        # Extract API Gateway endpoint
        api_gateway_endpoint = event.get('APIGatewayEndpoint')
        if not api_gateway_endpoint:
            raise ValueError("APIGatewayEndpoint not found in event")
        
        logger.debug(f'apigwEndpoint: {api_gateway_endpoint}')
        
        # Construct approval and rejection URLs
        encoded_task_token = quote_plus(task_token)
        encoded_execution_name = quote_plus(execution_name)
        encoded_state_machine_name = quote_plus(state_machine_name)
        approve_endpoint = (
            f"{api_gateway_endpoint}/execution"
            f"?action=approve"
            f"&ex={encoded_execution_name}"
            f"&sm={encoded_state_machine_name}"
            f"&taskToken={encoded_task_token}"
        )
        
        reject_endpoint = (
            f"{api_gateway_endpoint}/execution"
            f"?action=reject"
            f"&ex={encoded_execution_name}"
            f"&sm={encoded_state_machine_name}"
            f"&taskToken={encoded_task_token}"
        )
        
        logger.debug(f'approveEndpoint: {approve_endpoint}')
        logger.debug(f'rejectEndpoint: {reject_endpoint}')
        
        # Construct email message
        email_message = (
            "Welcome!\n\n"
            "This is an email requiring an approval for a step functions execution.\n\n"
            "Check the following information and click \"Approve\" link if you want to approve.\n\n"
            f"Execution Name -> {execution_name}\n\n"
            f"Approve {approve_endpoint}\n\n"
            f"Reject {reject_endpoint}\n\n"
            "Thanks for using Step functions!"
        )
        
        # Prepare response
        response = {
            'statusCode': 200,
            'result': 'SUCCESS',
            'emailMessage': email_message,
            'emailSubject': 'Required approval from AWS Step Functions',
            'approveEndpoint': approve_endpoint,
            'rejectEndpoint': reject_endpoint,
            'executionName': execution_name,
            'stateMachineName': state_machine_name
        }
        
        logger.info('Email content generated successfully')
        logger.debug(f'Response: {response}')
        
        # Publish to SNS if topic ARN is provided
        if sns_topic_arn:
            try:
                sns = boto3.client('sns')
                sns_response = sns.publish(
                    TopicArn=sns_topic_arn,
                    Message=email_message,
                    Subject=response['emailSubject']
                )
                logger.info(f'Email published to SNS. MessageId: {sns_response.get("MessageId")}')
                response['snsMessageId'] = sns_response.get('MessageId')
            except ClientError as e:
                logger.error(f'Failed to publish to SNS: {str(e)}')
                response['snsError'] = str(e)
        else:
            logger.info('SNS topic ARN not provided, skipping SNS publish')
        
        return response
        
    except ClientError as e:
        logger.error(f'AWS service error: {str(e)}')
        return {
            'statusCode': 500,
            'result': 'ERROR',
            'error': f'AWS service error: {str(e)}'
        }
    except Exception as e:
        logger.error(f'Error processing approval email: {str(e)}')
        return {
            'statusCode': 500,
            'result': 'ERROR',
            'error': str(e)
        }