import boto3
import pytest
import os
import json
from time import sleep
from handler import (
    TGWAttachment,
    CloudTrailEvent,
  #  accept_tgw_attachment,
    validate_vpc_in_ipam,
   # validate_user_identity,
  #  tag_attachment
)

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# Mock AWS settings
region = "us-west-2"
vpc = "vpc-12345678"
subnet = "subnet-12345678"
name = "Test"

ALLOWED_PRINCIPAL_PATTERNS = []

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

@pytest.mark.skip(reason="Moto does not yet support the accept_transit_gateway_vpc_attachment action")
@mock_aws
def test_accept_tgw_attachment_success(ec2):
    """
    Test accept_tgw_attachment successfully accepts a TGW VPC attachment.
    """

    # Create Transit Gateway
    tgw_id = ec2.create_transit_gateway(
        Description="Test TGW",
        Options={"DefaultRouteTableAssociation": "disable", "DefaultRouteTablePropagation": "disable"},
    )['TransitGateway']['TransitGatewayId']

    # Create Transit Gateway VPC Attachment
    attach = ec2.create_transit_gateway_vpc_attachment(
        TransitGatewayId=tgw_id,
        VpcId=vpc,
        SubnetIds=[subnet],
    )['TransitGatewayVpcAttachment']
    attachment_id = attach['TransitGatewayAttachmentId']

    # Call accept function
    result = accept_tgw_attachment(attachment_id)
    assert result is True

@pytest.mark.skip(reason="Moto does not yet support the get_ipam_pool_allocations action")
@mock_aws
def test_validate_vpc_in_ipam_no_allocation(ec2):
    """
    validate_vpc_in_ipam should return False when no IPAM allocations exist.
    """
    assert validate_vpc_in_ipam(ACCOUNT_ID, vpc) is False

