import json
import os
import logging
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from urllib.parse import unquote_plus

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

# Environment variables
email_addresses_env = os.environ.get('EMAIL_ADDRESSES', 'user@example.com')
email_addresses = [email.strip() for email in email_addresses_env.split(',') if email.strip()]

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to handle approval/rejection callbacks from API Gateway to Step Functions.
    
    This function processes approval or rejection actions from API Gateway query parameters,
    sends the result to Step Functions, and redirects to the AWS console execution page.
    
    Args:
        event: API Gateway event containing query parameters (action, taskToken, sm, ex)
        context: Lambda context object
        
    Returns:
        Dict containing HTTP response with redirect to Step Functions console
    """
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')
    
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters') or event.get('query', {})
        if not query_params:
            raise ValueError("No query parameters found in event")
        
        action = query_params.get('action')
        task_token = query_params.get('taskToken')
        state_machine_name = query_params.get('sm')
        execution_name = query_params.get('ex')
        
        logger.debug(f'action: {action}')
        logger.debug(f'taskToken (raw): {task_token}')
        logger.debug(f'statemachineName: {state_machine_name}')
        logger.debug(f'executionName: {execution_name}')
        
        # Validate required parameters
        if not all([action, task_token, state_machine_name, execution_name]):
            missing_params = [param for param, value in [
                ('action', action), ('taskToken', task_token), 
                ('sm', state_machine_name), ('ex', execution_name)
            ] if not value]
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        # URL decode the task token once (API Gateway may have already decoded it via VTL)
        # Try both raw and decoded versions if the first fails
        decoded_task_token = unquote_plus(task_token)
        logger.debug(f'taskToken (decoded): {decoded_task_token}')
        
        # Prepare message based on action
        email_list = ', '.join(email_addresses) if len(email_addresses) > 1 else email_addresses[0]
        if action == "approve":
            message = {"Status": f"Approved! Task approved by {email_list}"}
        elif action == "reject":
            message = {"Status": f"Rejected! Task rejected by {email_list}"}
        else:
            raise ValueError(f"Unrecognized action: {action}. Expected: approve, reject")
        
        logger.info(f'Processing {action} action for execution {execution_name}')
        
        # Send task success to Step Functions
        stepfunctions = boto3.client('stepfunctions')
        
        # Try with decoded token first, then fall back to raw token if that fails
        try:
            stepfunctions.send_task_success(
                output=json.dumps(message),
                taskToken=decoded_task_token
            )
            logger.info('Successfully sent task success to Step Functions with decoded token')
        except ClientError as e:
            if 'InvalidToken' in str(e):
                logger.warning('Decoded token failed, trying raw token')
                stepfunctions.send_task_success(
                    output=json.dumps(message),
                    taskToken=task_token
                )
                logger.info('Successfully sent task success to Step Functions with raw token')
            else:
                raise
        
        # Construct redirect URL to Step Functions console
        redirect_url = _construct_console_redirect_url(
            context.invoked_function_arn,
            state_machine_name,
            execution_name
        )
        
        logger.info(f'Redirecting to: {redirect_url}')
        
        # Return redirect response
        return {
            'statusCode': 302,
            'headers': {
                'Location': redirect_url
            },
            'body': json.dumps({
                'message': f'Task {action}d successfully',
                'redirectUrl': redirect_url
            })
        }
        
    except ClientError as e:
        logger.error(f'AWS service error: {str(e)}')
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'AWS service error',
                'message': str(e)
            })
        }
    except Exception as e:
        logger.error(f'Error processing approval callback: {str(e)}')
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Failed to process request',
                'message': str(e)
            })
        }


def _construct_console_redirect_url(lambda_arn: str, state_machine_name: str, execution_name: str) -> str:
    """
    Construct AWS Step Functions console URL for the execution.
    
    Args:
        lambda_arn: The Lambda function ARN to extract region and account info
        state_machine_name: Name of the state machine
        execution_name: Name of the execution
        
    Returns:
        URL to the Step Functions console execution page
    """
    # Parse Lambda ARN: arn:partition:lambda:region:account-id:function:function-name
    arn_parts = lambda_arn.split(':')
    if len(arn_parts) < 5:
        raise ValueError(f"Invalid Lambda ARN format: {lambda_arn}")
    
    partition = arn_parts[1]
    region = arn_parts[3]
    account_id = arn_parts[4]
    
    logger.debug(f'partition: {partition}')
    logger.debug(f'region: {region}')
    logger.debug(f'accountId: {account_id}')
    
    # Construct execution ARN
    execution_arn = f"arn:{partition}:states:{region}:{account_id}:execution:{state_machine_name}:{execution_name}"
    logger.debug(f'executionArn: {execution_arn}')
    
    # Construct console URL
    console_url = f"https://console.aws.amazon.com/states/home?region={region}#/executions/details/{execution_arn}"
    
    return console_url