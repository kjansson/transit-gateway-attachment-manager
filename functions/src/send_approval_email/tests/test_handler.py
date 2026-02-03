import pytest
import os
from unittest.mock import patch, MagicMock
from moto import mock_sns
import boto3

# Set environment variables before importing the handler
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['SNS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-topic'

from send_approval_email.handler import lambda_handler


class TestSendApprovalEmailHandler:
    """Test cases for the send approval email Lambda handler."""
    
    def test_successful_email_generation(self):
        """Test successful generation of approval email content."""
        event = {
            'ExecutionContext': {
                'Execution': {
                    'Name': 'test-execution-123'
                },
                'StateMachine': {
                    'Name': 'test-state-machine'
                },
                'Task': {
                    'Token': 'AAAAKgAAAAIAAAAAAAAAAR1VdMVvhzlPuudgWqQTqjgAAAAAIAAAAAAxJhKn1dYZHC8seTXGGZdVIIqbWfXFKYXEW7Xm8g=='
                }
            },
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        result = lambda_handler(event, MagicMock())
        
        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'
        assert 'emailMessage' in result
        assert 'emailSubject' in result
        assert result['emailSubject'] == 'Required approval from AWS Step Functions'
        assert 'approveEndpoint' in result
        assert 'rejectEndpoint' in result
        assert result['executionName'] == 'test-execution-123'
        assert result['stateMachineName'] == 'test-state-machine'
        
        # Verify URLs are properly constructed
        assert 'action=approve' in result['approveEndpoint']
        assert 'action=reject' in result['rejectEndpoint']
        assert 'ex=test-execution-123' in result['approveEndpoint']
        assert 'sm=test-state-machine' in result['approveEndpoint']
        assert 'taskToken=' in result['approveEndpoint']
        
        # Verify email message content
        email_message = result['emailMessage']
        assert 'Welcome!' in email_message
        assert 'test-execution-123' in email_message
        assert result['approveEndpoint'] in email_message
        assert result['rejectEndpoint'] in email_message
    
    @mock_sns
    def test_successful_email_generation_with_sns(self):
        """Test successful generation and SNS publishing of approval email content."""
        # Setup mock SNS
        sns = boto3.client('sns', region_name='us-east-1')
        topic_response = sns.create_topic(Name='test-topic')
        
        event = {
            'ExecutionContext': {
                'Execution': {
                    'Name': 'test-execution-123'
                },
                'StateMachine': {
                    'Name': 'test-state-machine'
                },
                'Task': {
                    'Token': 'AAAAKgAAAAIAAAAAAAAAAR1VdMVvhzlPuudgWqQTqjgAAAAAIAAAAAAxJhKn1dYZHC8seTXGGZdVIIqbWfXFKYXEW7Xm8g=='
                }
            },
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        with patch.dict(os.environ, {'SNS_TOPIC_ARN': topic_response['TopicArn']}):
            result = lambda_handler(event, MagicMock())
        
        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'
        assert 'snsMessageId' in result
        assert 'emailMessage' in result
    
    def test_sns_publish_failure(self):
        """Test handling of SNS publish failures."""
        event = {
            'ExecutionContext': {
                'Execution': {
                    'Name': 'test-execution-123'
                },
                'StateMachine': {
                    'Name': 'test-state-machine'
                },
                'Task': {
                    'Token': 'test-token'
                }
            },
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_sns = MagicMock()
            mock_sns.publish.side_effect = Exception("SNS publish failed")
            mock_boto_client.return_value = mock_sns
            
            result = lambda_handler(event, MagicMock())
            
            # Should still return success but with SNS error logged
            assert result['statusCode'] == 200
            assert result['result'] == 'SUCCESS'
            assert 'snsError' in result
    
    def test_no_sns_topic_arn(self):
        """Test behavior when SNS_TOPIC_ARN is not provided."""
        event = {
            'ExecutionContext': {
                'Execution': {
                    'Name': 'test-execution-123'
                },
                'StateMachine': {
                    'Name': 'test-state-machine'
                },
                'Task': {
                    'Token': 'test-token'
                }
            },
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        with patch.dict(os.environ, {'SNS_TOPIC_ARN': ''}, clear=False):
            result = lambda_handler(event, MagicMock())
            
            # Should still return success but skip SNS
            assert result['statusCode'] == 200
            assert result['result'] == 'SUCCESS'
            assert 'snsMessageId' not in result
    
    def test_missing_execution_context(self):
        """Test handling of missing ExecutionContext."""
        event = {
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        result = lambda_handler(event, MagicMock())
        
        assert result['statusCode'] == 500
        assert result['result'] == 'ERROR'
        assert 'ExecutionContext not found' in result['error']
    
    def test_missing_execution_name(self):
        """Test handling of missing execution name."""
        event = {
            'ExecutionContext': {
                'Execution': {},
                'StateMachine': {
                    'Name': 'test-state-machine'
                },
                'Task': {
                    'Token': 'test-token'
                }
            },
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        result = lambda_handler(event, MagicMock())
        
        assert result['statusCode'] == 500
        assert result['result'] == 'ERROR'
        assert 'Execution name not found' in result['error']
    
    def test_missing_state_machine_name(self):
        """Test handling of missing state machine name."""
        event = {
            'ExecutionContext': {
                'Execution': {
                    'Name': 'test-execution'
                },
                'StateMachine': {},
                'Task': {
                    'Token': 'test-token'
                }
            },
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        result = lambda_handler(event, MagicMock())
        
        assert result['statusCode'] == 500
        assert result['result'] == 'ERROR'
        assert 'StateMachine name not found' in result['error']
    
    def test_missing_task_token(self):
        """Test handling of missing task token."""
        event = {
            'ExecutionContext': {
                'Execution': {
                    'Name': 'test-execution'
                },
                'StateMachine': {
                    'Name': 'test-state-machine'
                },
                'Task': {}
            },
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        result = lambda_handler(event, MagicMock())
        
        assert result['statusCode'] == 500
        assert result['result'] == 'ERROR'
        assert 'Task token not found' in result['error']
    
    def test_missing_api_gateway_endpoint(self):
        """Test handling of missing API Gateway endpoint."""
        event = {
            'ExecutionContext': {
                'Execution': {
                    'Name': 'test-execution'
                },
                'StateMachine': {
                    'Name': 'test-state-machine'
                },
                'Task': {
                    'Token': 'test-token'
                }
            }
        }
        
        result = lambda_handler(event, MagicMock())
        
        assert result['statusCode'] == 500
        assert result['result'] == 'ERROR'
        assert 'APIGatewayEndpoint not found' in result['error']
    
    def test_url_encoding_of_task_token(self):
        """Test that task tokens with special characters are properly URL encoded."""
        event = {
            'ExecutionContext': {
                'Execution': {
                    'Name': 'test-execution'
                },
                'StateMachine': {
                    'Name': 'test-state-machine'
                },
                'Task': {
                    'Token': 'token+with/special=characters&more'
                }
            },
            'APIGatewayEndpoint': 'https://api.example.com'
        }
        
        result = lambda_handler(event, MagicMock())
        
        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'
        
        # Check that the task token is properly URL encoded
        assert 'token%2Bwith%2Fspecial%3Dcharacters%26more' in result['approveEndpoint']
        assert 'token%2Bwith%2Fspecial%3Dcharacters%26more' in result['rejectEndpoint']