# Send Approval Email Lambda Function

This Lambda function generates approval email content for AWS Step Functions human approval tasks and publishes it to an SNS topic.

## Purpose

Converts a Node.js CloudFormation-based Lambda function into Python, extracting execution context and API Gateway endpoint information to construct approval/rejection URLs, email message content, and automatically publish the email via SNS.

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

- `emailMessage`: The formatted email content
- `emailSubject`: The email subject line
- `approveEndpoint`: URL for approval action
- `rejectEndpoint`: URL for rejection action
- `executionName`: The execution name
- `stateMachineName`: The state machine name
- `snsMessageId`: The SNS message ID (if SNS publishing succeeded)
- `snsError`: Error message (if SNS publishing failed)

## Usage

This function is designed to be used within a Step Functions workflow that requires human approval. The function generates the email content and automatically publishes it to the configured SNS topic for delivery.

## Environment Variables

- `LOG_LEVEL`: Logging level (default: INFO)
- `SNS_TOPIC_ARN`: ARN of the SNS topic to publish approval emails to

## SNS Integration

The function automatically publishes the generated email to the specified SNS topic. If the SNS topic ARN is not provided or SNS publishing fails, the function will still return success but log the issue. This ensures the Step Functions workflow can continue even if email delivery encounters issues.

## Error Handling

The function validates all required fields in the input event and returns appropriate error messages if any are missing. SNS publishing errors are handled gracefully and logged without failing the entire function execution.

## AWS Permissions Required

- `sns:Publish` on the specified SNS topic