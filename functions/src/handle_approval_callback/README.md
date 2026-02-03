# Handle Approval Callback Lambda Function

This Lambda function handles approval/rejection callbacks from API Gateway to AWS Step Functions.

## Purpose

Converts a Node.js CloudFormation-based Lambda function into Python that processes approval or rejection actions triggered by email links, sends the result to Step Functions, and redirects users to the AWS console.

## Input Event Structure

The function expects an API Gateway event with query parameters:

```json
{
  "queryStringParameters": {
    "action": "approve|reject",
    "taskToken": "encoded-step-functions-task-token",
    "sm": "state-machine-name", 
    "ex": "execution-name"
  }
}
```

Alternative format is also supported:
```json
{
  "query": {
    "action": "approve|reject",
    "taskToken": "encoded-step-functions-task-token",
    "sm": "state-machine-name",
    "ex": "execution-name"
  }
}
```

## Query Parameters

- `action`: Must be either "approve" or "reject"
- `taskToken`: URL-encoded Step Functions task token (will be decoded automatically)
- `sm`: State machine name
- `ex`: Execution name

## Output

Returns an HTTP redirect response (302) that:

- Sends task success to Step Functions with approval/rejection status
- Redirects user to AWS Step Functions console execution page
- Includes success/error message in response body

## Environment Variables

- `LOG_LEVEL`: Logging level (default: INFO)
- `EMAIL_ADDRESSES`: Comma-separated list of email addresses to include in approval/rejection messages (default: user@example.com)
  - Single email: `user@example.com`
  - Multiple emails: `user1@example.com, user2@example.com, admin@example.com`

## Usage Flow

1. User receives approval email with approve/reject links
2. User clicks link, triggering API Gateway → this Lambda
3. Lambda validates parameters and sends result to Step Functions
4. Lambda redirects user to Step Functions console to view execution status

## Error Handling

The function validates all required parameters and provides appropriate HTTP status codes:

- `302`: Successful approval/rejection with redirect
- `400`: Bad request (missing/invalid parameters)
- `500`: AWS service errors (Step Functions failures)

## AWS Permissions Required

- `states:SendTaskSuccess` on the Step Functions state machine
- Standard Lambda execution role permissions