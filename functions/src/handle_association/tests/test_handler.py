import boto3
import pytest
import os
import json
from time import sleep
from handler import (
    associate_route_table,
    propagate_route_table,
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

@mock_aws
def test_associate_route_table_and_propagation(ec2):
    """
    Test associate_route_table and propagate_route_table functions.
    """
    # Create TGW and Route Table
    tgw = ec2.create_transit_gateway(
        Description="TGW for Tests",
        Options={"DefaultRouteTableAssociation": "disable",
                 "DefaultRouteTablePropagation": "disable"}
    )['TransitGateway']['TransitGatewayId']

    rt = ec2.create_transit_gateway_route_table(TransitGatewayId=tgw)
    rt_id = rt['TransitGatewayRouteTable']['TransitGatewayRouteTableId']

    # Create VPC attachment
    attachment = _create_attachment(ec2, tgw, subnet, vpc, name)

    # Associate route table
    assoc_result = associate_route_table(attachment, rt_id)
    # Check if the association was successful
    assert assoc_result is True
    assocs = ec2.get_transit_gateway_route_table_associations(TransitGatewayRouteTableId=rt_id)
    assert any(a['TransitGatewayAttachmentId']==attachment for a in assocs['Associations'])

    # Propagate route table
    prop_result = propagate_route_table(attachment, rt_id)
    # Check if the propagation was successful
    assert prop_result is True
    props = ec2.get_transit_gateway_route_table_propagations(TransitGatewayRouteTableId=rt_id)
    assert any(p['TransitGatewayAttachmentId']==attachment for p in props['TransitGatewayRouteTablePropagations'])

@mock_aws
def test_tgwattachment_and_event_parsing():
    """
    Test TGWAttachment.from_accept_event and CloudTrailEvent.from_raw parsing.
    """
    raw_event = {
        'detail-type': 'AWS API Call via CloudTrail',
        'detail': {
            'responseElements': {
                'AcceptTransitGatewayVpcAttachmentResponse': {
                    'transitGatewayVpcAttachment': {
                        'vpcOwnerId': '222',
                        'vpcId': 'vpc-xyz',
                        'transitGatewayAttachmentId': 'tgw-xyz'
                    }
                }
            }
        }
    }
    ct_event = CloudTrailEvent.from_raw(raw_event)
    attachment = TGWAttachment.from_event(ct_event)
    assert attachment.account_id == '222'
    assert attachment.vpc_id == 'vpc-xyz'
    assert attachment.attachment_id == 'tgw-xyz'
    # Test JSON input
    raw_json = json.dumps({'detail-type': 'dt', 'detail': {}})
    ct_event2 = CloudTrailEvent.from_raw(raw_json)
    assert ct_event2.detail_type == 'dt'
    assert isinstance(ct_event2.detail, dict)

@mock_aws
def test_get_ec2_client_region():
    """
    Test that get_ec2_client returns an EC2 client configured with AWS_REGION.
    """
    # Override environment variable before module import
    os.environ['AWS_REGION'] = region
    # Reload main to pick up the new AWS_REGION
    import importlib
    import handler as handler
    importlib.reload(handler)

    client = handler.get_ec2_client()
    assert client.meta.region_name == region
