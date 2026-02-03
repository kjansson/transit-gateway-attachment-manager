import boto3
import os
import logging
from typing import Dict
from botocore.exceptions import ClientError

# Import shared models from common layer
from models import CloudTrailEvent, TGWAttachment

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(log_level)

# Environment variables
region_env = os.environ.get('AWS_REGION', 'eu-north-1')
default_associate_route_table_id = os.environ.get('DEFAULT_ASSOCIATE_ROUTE_TABLE_ID', '')

def lambda_handler(event, context):
    logger.info('Lambda invocation started')
    logger.debug(f'Raw event: {event}')

    ec2 = boto3.client('ec2', region_name=region_env)
    # Extract the original CloudTrail event from the Step Functions payload
    ct_event = CloudTrailEvent.from_raw(event)
    
    # Extract the GetPoolTagsPayload from the Step Functions payload
    pool_tags_payload = event.get('GetPoolTagsPayload')
    
    attachment = TGWAttachment.from_event(ct_event)
    logger.info(f"Processing accepted TGWAttachment: {attachment}")

    association_route_table_id = None
    
    if pool_tags_payload and pool_tags_payload.get('Payload'):
        payload = pool_tags_payload['Payload']
        association_route_table_id = payload.get('association')
        logger.info(f"Found route tables from pool tags - Association: {association_route_table_id}")

    if not association_route_table_id and default_associate_route_table_id:
        association_route_table_id = default_associate_route_table_id
        logger.info(f"Using default association route table: {association_route_table_id}")
    
    if not association_route_table_id: 
        logger.error("No association route table found in pool tags and no defaults configured")
        raise Exception("No association route table found in pool tags and no defaults configured")

    if association_route_table_id:
        logger.info(f"Associating attachment {attachment.attachment_id} to route table {association_route_table_id}")
        try:
            ec2.associate_transit_gateway_route_table(
                TransitGatewayRouteTableId=association_route_table_id,
                TransitGatewayAttachmentId=attachment.attachment_id
            )
            logger.info(f"Associated {attachment.attachment_id} to route table {association_route_table_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to associate attachment {attachment.attachment_id} to route table {association_route_table_id}")
            return False            

    logger.info(f"Association operations completed.")

    return {
        "statusCode": 200,
        "result": "SUCCESS",
        "message": f"Processed attachment {attachment.attachment_id}",
        "attachment": {
            "account_id": attachment.account_id,
            "vpc_id": attachment.vpc_id,
            "attachment_id": attachment.attachment_id
        },
        "operations": {
            "association": {
                "route_table_id": association_route_table_id
            },
        }
    }

