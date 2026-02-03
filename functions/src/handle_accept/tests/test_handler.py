import boto3
import pytest
import os
import json
from time import sleep
from handler import (
    TGWAttachment,
    CloudTrailEvent,
    accept_tgw_attachment,
    # validate_vpc_in_ipam,
    # validate_user_identity,
    # tag_attachment
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

# @pytest.mark.skip(reason="Moto does not yet support the get_ipam_pool_allocations action")
# @mock_aws
# def test_validate_vpc_in_ipam_no_allocation(ec2):
#     """
#     validate_vpc_in_ipam should return False when no IPAM allocations exist.
#     """
#     assert validate_vpc_in_ipam(ACCOUNT_ID, vpc) is False

# @mock_aws
# def test_cloudtrail_and_dataclass_parsing():
#     """
#     Test CloudTrailEvent.from_raw and TGWAttachment.from_create_event parsing.
#     """
#     raw_event = {
#         'detail-type': 'AWS API Call via CloudTrail',
#         'detail': {
#             'eventName': 'CreateTransitGatewayVpcAttachment',
#             'responseElements': {
#                 'CreateTransitGatewayVpcAttachmentResponse': {
#                     'transitGatewayVpcAttachment': {
#                         'vpcOwnerId': '222',
#                         'vpcId': 'vpc-abc',
#                         'transitGatewayAttachmentId': 'tgw-abc',
#                         'state': 'pendingAcceptance'
#                     }
#                 }
#             }
#         }
#     }
#     ct_event = CloudTrailEvent.from_raw(raw_event)
#     assert ct_event.detail_type == 'AWS API Call via CloudTrail'
#     attachment = TGWAttachment.from_create_event(ct_event)
#     assert attachment.account_id == '222'
#     assert attachment.vpc_id == 'vpc-abc'
#     assert attachment.attachment_id == 'tgw-abc'
#     assert attachment.state == 'pendingAcceptance'
#     # Test JSON string input
#     json_str = json.dumps(raw_event)
#     ct_event2 = CloudTrailEvent.from_raw(json_str)
#     assert ct_event2.detail_type == 'AWS API Call via CloudTrail'
#     assert isinstance(ct_event2.detail, dict)

# def _create_attachment(ec2, tgw_id):

#     resp = ec2.create_transit_gateway_vpc_attachment(
#         TransitGatewayId=tgw_id,
#         VpcId=vpc,
#         SubnetIds=[subnet],
#         TagSpecifications=[
#             {
#                 "ResourceType": "transit-gateway-attachment",
#                 "Tags": [
#                     {"Key": "Name", "Value": name},
#                 ],
#             }
#         ],
#     )['TransitGatewayVpcAttachment']
#     att_id = resp['TransitGatewayAttachmentId']
#     state = None
#     while state != 'available':
#         state = ec2.describe_transit_gateway_vpc_attachments(
#             TransitGatewayAttachmentIds=[att_id]
#         )['TransitGatewayVpcAttachments'][0]['State']
#         sleep(0.1)
#     return att_id

# @mock_aws
# def test_tag_attachment_merges_single_tag_from_event(ec2):
#     # Create TGW
#     tgw_id = ec2.create_transit_gateway(
#         Description="Test TGW",
#         Options={"DefaultRouteTableAssociation": "disable", "DefaultRouteTablePropagation": "disable"}
#     )['TransitGateway']['TransitGatewayId']
#     # Create attachment
#     attach_id = _create_attachment(ec2, tgw_id)

#     # Fake CloudTrail event with single 'Tag'
#     raw_event = {
#         'detail-type': 'AWS API Call via CloudTrail',
#         'detail': {
#             'eventName': 'CreateTransitGatewayVpcAttachment',
#             'requestParameters': {
#                 'CreateTransitGatewayVpcAttachmentRequest': {
#                     'TransitGatewayId': tgw_id,
#                     'VpcId': vpc,
#                     'SubnetIds': {'item': subnet},
#                     'TagSpecifications': {
#                         'ResourceType': 'transit-gateway-attachment',
#                         'Tag': [
#                             {
#                                 'Value': name,
#                                 'tag': 1,
#                                 'Key': 'Name'
#                             },
#                             {
#                                 'Value': ACCOUNT_ID,
#                                 'tag': 2,
#                                 'Key': 'AccountId'
#                             }
#                         ]
#                     }
#                 }
#             }
#         }
#     }

#     ct_event = CloudTrailEvent.from_raw(raw_event)

#     # Call tag_attachment
#     tag_attachment(attach_id, vpc, ACCOUNT_ID, ct_event)

#     # Verify tags: original Name plus Env plus AutoAccepted
#     all_tags = ec2.describe_tags(
#         Filters=[{'Name': 'resource-id', 'Values': [attach_id]}]
#     )['Tags']

#     keys = {t['Key']: t['Value'] for t in all_tags}
#     assert keys.get('Name') == name

# def test_validate_user_identity_empty_patterns():
#     """
#     validate_user_identity should return False when no patterns are configured,
#     regardless of the userIdentity type.
#     """
#     # Clear any existing patterns
#     ALLOWED_PRINCIPAL_PATTERNS.clear()

#     # AWSAccount identity uses principalId
#     user_identity_aws_account = {
#         'type': 'AWSAccount',
#         'principalId': f"{ACCOUNT_ID}:user@example.com"
#     }
#     # AssumedRole identity uses arn
#     user_identity_assumed_role = {
#         'type': 'AssumedRole',
#         'arn': f"arn:aws:sts::{ACCOUNT_ID}:assumedRole/testRole/user@example.com"
#     }

#     assert validate_user_identity(user_identity_aws_account,ALLOWED_PRINCIPAL_PATTERNS ) is False
#     assert validate_user_identity(user_identity_assumed_role, ALLOWED_PRINCIPAL_PATTERNS) is False


# @pytest.mark.parametrize("pattern,user_identity,expected", [
#     # Standard match account principalId
#     (
#         ['123456789012:user@example.com'],
#         {'type': 'AWSAccount', 'principalId': '123456789012:user@example.com'},
#         True
#     ),
#     # baduser should not match AWSAccount principalId
#     (
#         ['123456789012:user@example.com'],
#         {'type': 'AWSAccount', 'principalId': "123456789012:baduser@example.com"},
#         False
#     ),
# ])

# def test_validate_user_identity_pattern(pattern, user_identity, expected):
#     """
#     Test validate_user_identity with different patterns and user identities.
#     """

#     ALLOWED_PRINCIPAL_PATTERNS[:] = pattern
#     result = validate_user_identity(user_identity, ALLOWED_PRINCIPAL_PATTERNS)
#     assert result is expected

# @mock_aws
# def test_get_ec2_client_region():
#     """
#     Test that get_ec2_client returns an EC2 client configured with AWS_REGION.
#     """
#     # Override environment variable before module import
#     os.environ['AWS_REGION'] = 'eu-west-1'
#     # Reload main to pick up the new AWS_REGION
#     import importlib
#     import handler as handler
#     importlib.reload(handler)

#     client = handler.get_ec2_client()
#     assert client.meta.region_name == 'eu-west-1'
