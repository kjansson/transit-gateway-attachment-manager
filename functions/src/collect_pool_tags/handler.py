import os
import logging
import boto3
from typing import Dict
from botocore.exceptions import ClientError

from models import CloudTrailEvent, TGWAttachment

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

# Environment variables
region_env = os.environ.get('AWS_REGION', 'eu-north-1')
ipam_pool_ids = os.environ.get('IPAM_POOL_IDS')
ipam_association_tag_key = os.environ.get('IPAM_ASSOCIATION_TAG_KEY')
ipam_propagation_tag_key = os.environ.get('IPAM_PROPAGATION_TAG_KEY')

def lambda_handler(event, context):
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')
    
    ct_event = CloudTrailEvent.from_raw(event)

    # Parse IPAM pool IDs from environment variable
    ipam_pool_id_list = [p.strip() for p in ipam_pool_ids.split(',') if p.strip()]

    if not ipam_pool_id_list:
        logger.info('IPAM functionality disabled (no IPAM_POOL_IDS provided)')
        return {
            'statusCode': 200,
            'result': "SKIPPED",
            'body': 'IPAM functionality disabled (no IPAM_POOL_IDS provided)'
        }
    
    if ipam_association_tag_key is None and ipam_propagation_tag_key is None:
        logger.info('IPAM tag keys not configured, skipping IPAM tag retrieval')
        return {
            'statusCode': 200,
            'result': "SKIPPED",
            'body': 'IPAM tag keys not configured, skipping IPAM tag retrieval'
        }

    attachment = TGWAttachment.from_event(ct_event)
    attachment_ipam_pool_id = None
    for ipam_pool_id in ipam_pool_id_list:
        ec2 = boto3.client('ec2', region_name=region_env)
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
                    attachment_ipam_pool_id = ipam_pool_id
                    break
            next_token = resp.get('NextToken')
            if not next_token:
                break

    if attachment_ipam_pool_id:
        logger.info(f"VPC {attachment.vpc_id} is associated with IPAM pool {attachment_ipam_pool_id}")
    else:
        logger.error(f"No IPAM allocation found for VPC {attachment.vpc_id} in any of the specified IPAM pools")
        raise ValueError(f"No IPAM allocation found for VPC {attachment.vpc_id} in any of the specified IPAM pools")

    try:
        ec2 = boto3.client('ec2', region_name=region_env)

        logger.info(f"Retrieving tags for IPAM pool: {ipam_pool_id}")
        response = ec2.describe_ipam_pools(IpamPoolIds=[ipam_pool_id])

        if not response.get('IpamPools'):
            logger.error(f"IPAM pool {ipam_pool_id} not found")
            raise ValueError(f"IPAM pool {ipam_pool_id} not found")
        
        pool = response['IpamPools'][0]
        tags = pool.get('Tags', [])
        
        # Convert list of tag dictionaries to a simple key-value dictionary
        tag_dict = {tag['Key']: tag['Value'] for tag in tags}
        
        logger.info(f"Found {len(tag_dict)} route table tags for IPAM pool {ipam_pool_id}")
        logger.debug(f"Pool tags: {tag_dict}")
        logger.debug(f"Association tag key: {ipam_association_tag_key}")
        logger.debug(f"Propagation tag key: {ipam_propagation_tag_key}")

        logger.info(f"Successfully retrieved route table tags for IPAM pool {ipam_pool_id}")

        return {
            'statusCode': 200,
            'result': "SUCCESS",
            'ipam_pool_id': ipam_pool_id,
            'association': tag_dict.get(ipam_association_tag_key),
            'propagation': tag_dict.get(ipam_propagation_tag_key),
        }
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Failed to retrieve IPAM pool tags: {error_code} - {error_message}")
        raise

