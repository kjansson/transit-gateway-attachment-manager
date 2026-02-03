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

def lambda_handler(event, context):
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')
    ct_event = CloudTrailEvent.from_raw(event)

    # Parse attachment including state
    attachment = TGWAttachment.from_event(ct_event)
    if attachment.state != 'pendingAcceptance':
        logger.info(f"Skipping attachment with state: {attachment.state}")
        return {
            'result': "SKIPPED",
            'message': f"Attachment is in {attachment.state} state"
        }
    ec2 = boto3.client('ec2', region_name=region_env)
    try:
        ec2.accept_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attachment.attachment_id)
        logger.info(f"Accepted TGW attachment {attachment.attachment_id}")
    except Exception as e:
        logger.error(f"Failed to accept TGW attachment {attachment.attachment_id}: {e}")
        raise

    logger.info(f"Completed processing for TGWAttachment: {attachment}")
    return {
        'result': "SUCCESS",
        'message': f"Accepted attachment {attachment.attachment_id}"
    }
