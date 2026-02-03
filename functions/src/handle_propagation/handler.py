import boto3
import os
import logging
from typing import Dict
from botocore.exceptions import ClientError

# Import shared models
from models import CloudTrailEvent, TGWAttachment

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

# Environment variables
region_env = os.environ.get('AWS_REGION', 'eu-north-1')
default_propagate_route_table_ids = os.environ.get('DEFAULT_PROPAGATE_ROUTE_TABLE_IDS', '')

def lambda_handler(event, context):
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')

    # Extract the original CloudTrail event from the Step Functions payload
    ct_event = CloudTrailEvent.from_raw(event)
    
    # Extract the GetPoolTagsPayload from the Step Functions payload
    pool_tags_payload = event.get('GetPoolTagsPayload')
    
    attachment = TGWAttachment.from_event(ct_event)
    logger.info(f"Processing accepted TGWAttachment: {attachment}")
    ec2 = boto3.client('ec2', region_name=region_env)
    # Find route tables from GetPoolTagsPayload and split by comma if multiple

    propagation_route_table_ids = []
    if pool_tags_payload and pool_tags_payload.get('Payload'):
        payload = pool_tags_payload['Payload']
        propagation_id = payload.get('propagation')
        if propagation_id:
            propagation_route_table_ids = [r.strip() for r in propagation_id.split(',') if r.strip()]
            logger.info(f"Found route tables from pool tags - Propagations: {propagation_route_table_ids}")
    
    if not propagation_route_table_ids and default_propagate_route_table_ids:
        propagation_route_table_ids = [r.strip() for r in default_propagate_route_table_ids.split(',') if r.strip()]
        logger.info(f"Using default propagation route tables: {propagation_route_table_ids}")

    if not propagation_route_table_ids: 
        logger.error("No route tables found in pool tags and no defaults configured")
        raise Exception("No route tables found in pool tags and no defaults configured")

    propagation_successes = []
    if propagation_route_table_ids:
        for route_table_id in propagation_route_table_ids:
            logger.info(f"Enabling propagation for attachment {attachment.attachment_id} to route table {route_table_id}")
            try:
                ec2.enable_transit_gateway_route_table_propagation(
                    TransitGatewayRouteTableId=route_table_id,
                    TransitGatewayAttachmentId=attachment.attachment_id
                )
                propagation_successes.append(True)
                logger.info(f"Enabled propagation for {attachment.attachment_id} to route table {route_table_id}")
            except ClientError as e:
                logger.error(f"Failed to enable propagation for attachment {attachment.attachment_id} to route table {route_table_id}")

    overall_success = all(propagation_successes)
    logger.info(f"Propagations operations completed. Overall success: {overall_success}")

    if overall_success:
        return {
            "statusCode": 200 ,
            "result": "SUCCESS",
            "message": f"Processed attachment {attachment.attachment_id}",
            "attachment": {
                "account_id": attachment.account_id,
                "vpc_id": attachment.vpc_id,
                "attachment_id": attachment.attachment_id
            },
            "operations": {
                "propagations": [
                    {
                        "route_table_id": rt_id,
                    }
                    for rt_id in propagation_route_table_ids
                ]
            }
        }
    else:
        logger.error(f"One or more propagation operations failed for attachment {attachment.attachment_id}")
        raise Exception(f"One or more propagation operations failed for attachment {attachment.attachment_id}")
