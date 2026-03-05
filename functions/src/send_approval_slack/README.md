# Send Approval Slack Lambda Function

This Lambda function sends an approval message to Slack for AWS Step Functions human approval tasks.

## Purpose

Posts an approval message to a Slack channel via webhook URL, extracting execution context and API Gateway endpoint information to construct approval/rejection URLs. Uses the same message format as the email-based approval function.

## Input Event Structure

The function expects an event with the following structure:

```json
{
  "ExecutionContext": {
    "Execution": {
      "Name": "execution-name"
    },
    "StateMachine": {
      "Name": "state-machine-name"
    },
    "Task": {
      "Token": "task-token"
    }
  },
  "APIGatewayEndpoint": "https://api.example.com"
}
```

## Output

Returns a response containing:

- `message`: The formatted message content
- `subject`: The message subject line
- `approveEndpoint`: URL for approval action
- `rejectEndpoint`: URL for rejection action
- `executionName`: The execution name
- `stateMachineName`: The state machine name
- `slackResponse`: The Slack API response (if posting succeeded)
- `slackError`: Error message (if Slack posting failed)

## Usage

This function is designed to be used within a Step Functions workflow that requires human approval. It serves as an alternative to the email-based approval function, posting the approval message to a Slack channel instead.

## Environment Variables

- `LOG_LEVEL`: Logging level (default: INFO)
- `SLACK_WEBHOOK_URL`: Slack incoming webhook URL to post approval messages to

## Error Handling

The function validates all required fields in the input event and returns appropriate error messages if any are missing. Slack posting errors are handled gracefully and logged without failing the entire function execution.

## AWS Permissions Required

No additional AWS permissions are required. The function communicates with Slack via HTTPS webhook.