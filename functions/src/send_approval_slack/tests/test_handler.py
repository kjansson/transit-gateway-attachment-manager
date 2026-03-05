import pytest
import os
import json
from unittest.mock import patch, MagicMock, Mock
from urllib.error import HTTPError, URLError
from io import BytesIO

# Set environment variables before importing the handler
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['SLACK_WEBHOOK_URL'] = 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

from send_approval_slack.handler import lambda_handler


class TestSendApprovalSlackHandler:
    """Test cases for the send approval Slack Lambda handler."""

    def test_successful_message_generation(self):
        """Test successful generation of approval message content."""
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

        with patch('send_approval_slack.handler.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'ok'
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = lambda_handler(event, MagicMock())

        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'
        assert 'message' in result
        assert 'subject' in result
        assert result['subject'] == 'Required approval from AWS Step Functions'
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

        # Verify message content matches email format
        message = result['message']
        assert 'Welcome!' in message
        assert 'test-execution-123' in message
        assert result['approveEndpoint'] in message
        assert result['rejectEndpoint'] in message

    def test_successful_slack_post(self):
        """Test successful posting to Slack webhook."""
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

        with patch('send_approval_slack.handler.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'ok'
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = lambda_handler(event, MagicMock())

        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'
        assert result['slackResponse'] == 'ok'

        # Verify the Slack payload
        call_args = mock_urlopen.call_args[0][0]
        payload = json.loads(call_args.data.decode('utf-8'))
        assert 'text' in payload
        assert 'Welcome!' in payload['text']

    def test_slack_post_http_error(self):
        """Test handling of Slack webhook HTTP errors."""
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

        with patch('send_approval_slack.handler.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                url='https://hooks.slack.com/services/test',
                code=403,
                msg='Forbidden',
                hdrs={},
                fp=BytesIO(b'invalid_token')
            )

            result = lambda_handler(event, MagicMock())

        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'
        assert 'slackError' in result

    def test_slack_post_url_error(self):
        """Test handling of Slack webhook URL errors."""
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

        with patch('send_approval_slack.handler.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = URLError('Connection refused')

            result = lambda_handler(event, MagicMock())

        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'
        assert 'slackError' in result

    def test_no_slack_webhook_url(self):
        """Test behavior when SLACK_WEBHOOK_URL is not provided."""
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

        with patch.dict(os.environ, {'SLACK_WEBHOOK_URL': ''}, clear=False):
            result = lambda_handler(event, MagicMock())

        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'
        assert 'slackResponse' not in result

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

        with patch('send_approval_slack.handler.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'ok'
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = lambda_handler(event, MagicMock())

        assert result['statusCode'] == 200
        assert result['result'] == 'SUCCESS'

        # Check that the task token is properly URL encoded
        assert 'token%2Bwith%2Fspecial%3Dcharacters%26more' in result['approveEndpoint']
        assert 'token%2Bwith%2Fspecial%3Dcharacters%26more' in result['rejectEndpoint']