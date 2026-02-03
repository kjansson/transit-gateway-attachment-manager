import boto3
import pytest
import os
import json
from time import sleep
from handler import (
    TGWAttachment,
    CloudTrailEvent,
)
from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# Mock AWS settings
region = "us-west-2"
vpc = "vpc-12345678"
subnet = "subnet-12345678"
name = "Test"

@pytest.fixture(scope='function')
def aws_credentials():
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_ID'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_REGION'] = region

@pytest.fixture(scope='function')
def ec2(aws_credentials):
    with mock_aws():
        yield boto3.client('ec2')

def _create_attachment(ec2, gateway_id, subnet_id, vpc_id, name):
    resp = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=gateway_id,
        VpcId=vpc_id,
        SubnetIds=[subnet_id],
        TagSpecifications=[
            {
                "ResourceType": "transit-gateway-attachment",
                "Tags": [
                    {"Key": "Name", "Value": name},
                    {"Key": "RequestId", "Value": "123456"},
                ],
            }
        ],
    )['TransitGatewayVpcAttachment']
    att_id = resp['TransitGatewayAttachmentId']
    status = None
    while status != 'available':
        status = ec2.describe_transit_gateway_vpc_attachments(
            TransitGatewayAttachmentIds=[att_id]
        )['TransitGatewayVpcAttachments'][0]['State']
        sleep(0.1)
    return att_id

