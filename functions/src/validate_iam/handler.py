import json
import os
import logging
import fnmatch
from typing import List

# Import shared models
from models import CloudTrailEvent, TGWAttachment

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

# Environment variables
region_env = os.environ.get('AWS_REGION', 'eu-north-1')
allowed_principal_patterns_env = os.environ.get('ALLOWED_PRINCIPAL_PATTERNS', '*')

def lambda_handler(event, context):
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')
    
    # Parse allowed principal patterns from environment variable
    allowed_principal_patterns = [p.strip() for p in allowed_principal_patterns_env.split(',') if p.strip()]
    logger.debug(f'Using allowed patterns from environment: {allowed_principal_patterns}')
    
    ct_event = CloudTrailEvent.from_raw(event)

    detail = ct_event.detail
    user_identity = detail.get('userIdentity', {})

    identity_type = user_identity.get('type', '')
    identity = user_identity.get('principalId') if identity_type == 'AWSAccount' else user_identity.get('arn', '')

    match = False
    for pattern in allowed_principal_patterns:
        if fnmatch.fnmatch(identity, pattern):
            logger.debug(f'Principal {identity} matched allowed pattern {pattern}')
            match = True

    if not match:
        logger.warning(f'Principal {identity} did not match any allowed patterns')
        raise PermissionError(f"Unauthorized principal: {identity} not in patterns {allowed_principal_patterns}")

    attachment = TGWAttachment.from_event(ct_event)
    logger.info(f"IAM validation completed successfully for attachment: {attachment}")
    return {
        'result': "SUCCESS",
        'attachment': {
            'account_id': attachment.account_id,
            'vpc_id': attachment.vpc_id,
            'attachment_id': attachment.attachment_id,
            'state': attachment.state,
            'requesting_principal': identity
        },
        'message': f"IAM validation passed for attachment {attachment.attachment_id}"
    }