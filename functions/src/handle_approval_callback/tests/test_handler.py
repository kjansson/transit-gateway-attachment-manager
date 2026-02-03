import pytest
import json
import os
from unittest.mock import patch, MagicMock
from moto import mock_stepfunctions
import boto3

# Set environment variables before importing the handler
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['EMAIL_ADDRESSES'] = 'test@example.com'

from handle_approval_callback.handler import lambda_handler, _construct_console_redirect_url


class TestHandleApprovalCallbackHandler:
    """Test cases for the handle approval callback Lambda handler."""
    
    @mock_stepfunctions
    def test_successful_approval(self):
        """Test successful approval callback."""
        # Setup mock Step Functions
        client = boto3.client('stepfunctions', region_name='us-east-1')
        
        event = {
            'queryStringParameters': {
                'action': 'approve',
                'taskToken': 'test-task-token',
                'sm': 'test-state-machine',
                'ex': 'test-execution'
            }
        }
        
        context = MagicMock()
        context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        
        with patch('boto3.client') as mock_boto_client:
            mock_sfn = MagicMock()
            mock_boto_client.return_value = mock_sfn
            
            result = lambda_handler(event, context)
            
            # Verify Step Functions call
            mock_sfn.send_task_success.assert_called_once_with(
                output='{"Status": "Approved! Task approved by test@example.com"}',
                taskToken='test-task-token'
            )
            
            # Verify response
            assert result['statusCode'] == 302
            assert 'Location' in result['headers']
            assert 'console.aws.amazon.com/states' in result['headers']['Location']
            
            body = json.loads(result['body'])
            assert body['message'] == 'Task approved successfully'
    
    @mock_stepfunctions  
    def test_successful_rejection(self):
        """Test successful rejection callback."""
        event = {
            'queryStringParameters': {
                'action': 'reject',
                'taskToken': 'test-task-token',
                'sm': 'test-state-machine',
                'ex': 'test-execution'
            }
        }
        
        context = MagicMock()
        context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        
        with patch('boto3.client') as mock_boto_client:
            mock_sfn = MagicMock()
            mock_boto_client.return_value = mock_sfn
            
            result = lambda_handler(event, context)
            
            # Verify Step Functions call
            mock_sfn.send_task_success.assert_called_once_with(
                output='{"Status": "Rejected! Task rejected by test@example.com"}',
                taskToken='test-task-token'
            )
            
            # Verify response
            assert result['statusCode'] == 302
            body = json.loads(result['body'])
            assert body['message'] == 'Task rejected successfully'
    
    @mock_stepfunctions
    def test_multiple_email_addresses(self):
        """Test handling of multiple email addresses."""
        # Temporarily set multiple email addresses
        original_env = os.environ.get('EMAIL_ADDRESSES')
        os.environ['EMAIL_ADDRESSES'] = 'user1@example.com, user2@example.com, user3@example.com'
        
        try:
            # Reload the module to pick up new environment variable
            import importlib
            import handle_approval_callback.handler
            importlib.reload(handle_approval_callback.handler)
            
            event = {
                'queryStringParameters': {
                    'action': 'approve',
                    'taskToken': 'test-task-token',
                    'sm': 'test-state-machine',
                    'ex': 'test-execution'
                }
            }
            
            context = MagicMock()
            context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
            
            with patch('boto3.client') as mock_boto_client:
                mock_sfn = MagicMock()
                mock_boto_client.return_value = mock_sfn
                
                result = handle_approval_callback.handler.lambda_handler(event, context)
                
                # Verify Step Functions call contains all email addresses
                mock_sfn.send_task_success.assert_called_once()
                call_args = mock_sfn.send_task_success.call_args[1]
                output = json.loads(call_args['output'])
                assert 'user1@example.com, user2@example.com, user3@example.com' in output['Status']
                
                # Verify response
                assert result['statusCode'] == 302
        finally:
            # Restore original environment
            if original_env:
                os.environ['EMAIL_ADDRESSES'] = original_env
            else:
                os.environ.pop('EMAIL_ADDRESSES', None)
            # Reload module again to restore original state
            importlib.reload(handle_approval_callback.handler)
    
    def test_url_encoded_task_token(self):
        """Test handling of URL-encoded task token."""
        event = {
            'queryStringParameters': {
                'action': 'approve',
                'taskToken': 'test%2Btask%2Ftoken%3Dwith%26special',  # URL encoded
                'sm': 'test-state-machine',
                'ex': 'test-execution'
            }
        }
        
        context = MagicMock()
        context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        
        with patch('boto3.client') as mock_boto_client:
            mock_sfn = MagicMock()
            mock_boto_client.return_value = mock_sfn
            
            result = lambda_handler(event, context)
            
            # Verify the task token was URL decoded before sending to Step Functions
            mock_sfn.send_task_success.assert_called_once_with(
                output='{"Status": "Approved! Task approved by test@example.com"}',
                taskToken='test+task/token=with&special'  # Should be decoded
            )
    
    def test_missing_query_parameters(self):
        """Test handling of missing query parameters."""
        event = {}
        context = MagicMock()
        
        result = lambda_handler(event, context)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'No query parameters found' in body['message']
    
    def test_missing_individual_parameters(self):
        """Test handling of missing individual required parameters."""
        event = {
            'queryStringParameters': {
                'action': 'approve',
                # Missing taskToken, sm, ex
            }
        }
        context = MagicMock()
        
        result = lambda_handler(event, context)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Missing required parameters' in body['message']
        assert 'taskToken' in body['message']
        assert 'sm' in body['message']
        assert 'ex' in body['message']
    
    def test_invalid_action(self):
        """Test handling of invalid action parameter."""
        event = {
            'queryStringParameters': {
                'action': 'invalid',
                'taskToken': 'test-token',
                'sm': 'test-state-machine',
                'ex': 'test-execution'
            }
        }
        context = MagicMock()
        
        result = lambda_handler(event, context)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Unrecognized action: invalid' in body['message']
    
    def test_stepfunctions_client_error(self):
        """Test handling of Step Functions client errors."""
        event = {
            'queryStringParameters': {
                'action': 'approve',
                'taskToken': 'test-token',
                'sm': 'test-state-machine',
                'ex': 'test-execution'
            }
        }
        
        context = MagicMock()
        context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        
        with patch('boto3.client') as mock_boto_client:
            mock_sfn = MagicMock()
            mock_sfn.send_task_success.side_effect = Exception("Invalid task token")
            mock_boto_client.return_value = mock_sfn
            
            result = lambda_handler(event, context)
            
            assert result['statusCode'] == 500
            body = json.loads(result['body'])
            assert 'AWS service error' in body['error']
    
    def test_alternative_query_format(self):
        """Test handling of alternative query parameter format (query instead of queryStringParameters)."""
        event = {
            'query': {
                'action': 'approve',
                'taskToken': 'test-token',
                'sm': 'test-state-machine',
                'ex': 'test-execution'
            }
        }
        
        context = MagicMock()
        context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        
        with patch('boto3.client') as mock_boto_client:
            mock_sfn = MagicMock()
            mock_boto_client.return_value = mock_sfn
            
            result = lambda_handler(event, context)
            
            assert result['statusCode'] == 302
            mock_sfn.send_task_success.assert_called_once()


class TestConsoleRedirectUrl:
    """Test cases for the console redirect URL construction."""
    
    def test_construct_console_redirect_url(self):
        """Test construction of AWS console redirect URL."""
        lambda_arn = 'arn:aws:lambda:us-west-2:123456789012:function:my-function'
        state_machine_name = 'MyStateMachine'
        execution_name = 'MyExecution'
        
        url = _construct_console_redirect_url(lambda_arn, state_machine_name, execution_name)
        
        expected_execution_arn = 'arn:aws:lambda:states:us-west-2:123456789012:execution:MyStateMachine:MyExecution'
        expected_url = f'https://console.aws.amazon.com/states/home?region=us-west-2#/executions/details/{expected_execution_arn}'
        
        assert 'us-west-2' in url
        assert 'MyStateMachine' in url
        assert 'MyExecution' in url
        assert 'console.aws.amazon.com/states' in url
    
    def test_construct_console_redirect_url_different_partition(self):
        """Test construction of URL with different AWS partition."""
        lambda_arn = 'arn:aws-gov:lambda:us-gov-west-1:123456789012:function:my-function'
        state_machine_name = 'MyStateMachine'
        execution_name = 'MyExecution'
        
        url = _construct_console_redirect_url(lambda_arn, state_machine_name, execution_name)
        
        assert 'us-gov-west-1' in url
        assert 'MyStateMachine' in url
        assert 'MyExecution' in url
    
    def test_invalid_lambda_arn(self):
        """Test handling of invalid Lambda ARN."""
        invalid_arn = 'invalid:arn'
        
        with pytest.raises(ValueError, match="Invalid Lambda ARN format"):
            _construct_console_redirect_url(invalid_arn, 'StateMachine', 'Execution')