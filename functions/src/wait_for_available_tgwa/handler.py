import boto3
import os
import logging
from botocore.exceptions import ClientError

# Import shared models
from models import CloudTrailEvent, TGWAttachment

# Configure logging
region_env = os.environ.get('AWS_REGION', 'eu-north-1')
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

def lambda_handler(event, context):
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')

    ct_event = CloudTrailEvent.from_raw(event)

    attachment = TGWAttachment.from_event(ct_event)

    ec2 = boto3.client('ec2', region_name=region_env)
    try:
        response = ec2.describe_transit_gateway_attachments(
            TransitGatewayAttachmentIds=[attachment.attachment_id]
        )
        state = response['TransitGatewayAttachments'][0]['State']
        logger.info(f"TGW Attachment {attachment.attachment_id} is in state: {state}")
    except ClientError as e:
        logger.error(f"Failed to describe TGW attachment {attachment.attachment_id}: {e}")

    if state == 'available':
        return {
            'result': "SUCCESS",
            'attachment': {
                'account_id': attachment.account_id,
                'vpc_id': attachment.vpc_id,
                'attachment_id': attachment.attachment_id,
                'state': attachment.state
            },
            'message': f"Attachment {attachment.attachment_id} is available"
        }
    else:
        raise Exception(f"Attachment {attachment.attachment_id} is in state {state}, expected 'available'")


