# Lambda Functions for AWS Transit Gateway Auto-Accept Module

This directory contains the Lambda functions used in the AWS Transit Gateway Auto-Accept Module. These functions automate the lifecycle management of Transit Gateway VPC attachments, ensuring seamless integration and efficient operations.

## Local Development and Testing

### Setting Up the Environment

This project uses `uv` for managing Python environments and running tasks. To get started with `uv`, follow the installation instructions provided in the [official documentation](https://docs.astral.sh/uv/getting-started/installation/). Detailed instructions for working with `uv` will be added here as needed.

To work on the Lambda functions locally, ensure you have the required dependencies installed. Use the `pyproject.toml` file in each function's directory to manage dependencies. You can install them using the following command:

```bash
uv sync
```

### Running Tests

Testing can be performed from the root of this directory. For example, to test the `handle_create` function, run:

```bash
uv run pytest src/handle_create
```

### Using Moto for Testing

This project also uses the [Moto](https://docs.getmoto.org/en/latest/docs/getting_started.html) library for testing AWS resource creation with Boto3. Moto allows you to mock a number of AWS services (not all), enabling you to write unit tests without making actual calls to AWS. This ensures faster and cost-effective testing of your Lambda functions.

### Sample Events

The `events/` folder contains sample event JSON files that can be used to test the Lambda functions locally. These events simulate AWS service events and provide a starting point for writing and debugging your functions.

- `AcceptTransitGatewayVpcAttachment.json`: Simulates an event for accepting a Transit Gateway VPC attachment.
- `CreateTransitGatewayVpcAttachmentRequest.json`: Simulates an event for creating a Transit Gateway VPC attachment.
