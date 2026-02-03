import json
import boto3
import os
import logging
from botocore.exceptions import ClientError

# Import shared models
from models import CloudTrailEvent, TGWAttachment

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'DEBUG').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

# Environment variables
region_env = os.environ.get('AWS_REGION', 'eu-north-1')
ipam_pool_ids = os.environ.get('IPAM_POOL_IDS', 'NONE')

def lambda_handler(event, context):
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')

    ct_event = CloudTrailEvent.from_raw(event)

    # Parse attachment including state
    attachment = TGWAttachment.from_event(ct_event)
    if attachment.state != 'pendingAcceptance':
        logger.info(f"Skipping attachment with state: {attachment.state}")
        raise ValueError(f"Attachment not in pendingAcceptance state: {attachment.state}")

    # Parse IPAM pool IDs from environment variable
    ipam_pool_id_list = [p.strip() for p in ipam_pool_ids.split(',') if p.strip()]

    found_ipam_allocation = False
    for ipam_pool_id in ipam_pool_id_list:
        ec2 = boto3.client('ec2', region_name=region_env)
        found_ipam_allocation = False
        containing_pool = ""
        next_token = None
        while True:
            params = {'IpamPoolId': ipam_pool_id}
            if next_token:
                params['NextToken'] = next_token
            resp = ec2.get_ipam_pool_allocations(**params)
            allocations = resp.get('IpamPoolAllocations', [])
            for alloc in allocations:
                if alloc.get('ResourceId') == attachment.vpc_id:
                    logger.info(f"Found IPAM allocation for VPC {attachment.vpc_id} in pool {ipam_pool_id}")
                    found_ipam_allocation = True
                    containing_pool = ipam_pool_id
                    break
            next_token = resp.get('NextToken')
            if not next_token:
                break

    if not found_ipam_allocation:
        logger.error(f"VPC {attachment.vpc_id} in account {attachment.account_id} is not allocated in any of the specified IPAM pools: {ipam_pool_id_list}")
        raise Exception(f"VPC {attachment.vpc_id} in account {attachment.account_id} is not allocated in any of the specified IPAM pools: {ipam_pool_id_list}")
    
    logger.info(f"IPAM validation completed successfully for attachment: {attachment}")
    return {
        'result': "SUCCESS",
        'attachment': {
            'account_id': attachment.account_id,
            'vpc_id': attachment.vpc_id,
            'attachment_id': attachment.attachment_id,
            'state': attachment.state,
            'ipam_pool_id': containing_pool
        },
        'message': f"IPAM validation passed for attachment {attachment.attachment_id}"
    }
