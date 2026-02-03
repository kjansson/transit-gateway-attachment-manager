import boto3
import os
import logging
from botocore.exceptions import ClientError

# Import shared models from common layer
from models import CloudTrailEvent, TGWAttachment

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

# Environment variables
region_env = os.environ.get('AWS_REGION', 'eu-north-1')
attachment_tag_key = os.environ.get('ATTACHMENT_TAG_KEY', '')
attachment_tag_value = os.environ.get('ATTACHMENT_TAG_VALUE', '')

def lambda_handler(event, context):
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')
    ct_event = CloudTrailEvent.from_raw(event)

    # Parse attachment including state
    attachment = TGWAttachment.from_event(ct_event)

    if not attachment_tag_key or not attachment_tag_value:
        logger.info("No attachment tag key/value configured, skipping tagging")
        return {
            'result': "SKIPPED",
            'message': "No attachment tag key/value configured"
        }
    ec2 = boto3.client('ec2', region_name=region_env)
    try:
        ec2.create_tags(
            Resources=[attachment.attachment_id],
            Tags=[
                {
                    'Key': attachment_tag_key,
                    'Value': attachment_tag_value
                }
            ]
        )
        logger.info(f"Tagged TGW attachment {attachment.attachment_id} with {attachment_tag_key}:{attachment_tag_value}")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Failed to tag TGW attachment {attachment.attachment_id}: {error_code} - {error_message}")
        raise
