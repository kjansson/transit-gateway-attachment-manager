"""
Common data models for TGW auto-accept system.

This module contains shared dataclasses used across multiple Lambda functions
to avoid code duplication and ensure consistent data structures.
"""

import json
from dataclasses import dataclass
from typing import Dict


@dataclass
class CloudTrailEvent:
    """
    Represents a CloudTrail event received from EventBridge.
    
    Attributes:
        detail_type: The type of event (e.g., "AWS API Call via CloudTrail")
        detail: The detailed event data from CloudTrail
    """
    detail_type: str
    detail: Dict

    @classmethod
    def from_raw(cls, raw_event) -> 'CloudTrailEvent':
        """
        Create a CloudTrailEvent from raw event data.
        
        Args:
            raw_event: Raw event data (JSON string or dict)
            
        Returns:
            CloudTrailEvent instance
        """
        try:
            data = json.loads(raw_event)
        except (TypeError, ValueError):
            data = raw_event
        return cls(
            detail_type=data.get('detail-type', ''),
            detail=data.get('detail', {})
        )


@dataclass
class TGW:
    """
    Represents a Transit Gateway.
    
    Attributes:
        tgw_id: identifier of the Transit Gateway
    """
    tgw_id: str

    @classmethod
    def from_event(cls, ct_event: CloudTrailEvent) -> 'TGW':
        """
        Create a TGW from an AcceptTransitGatewayVpcAttachment CloudTrail event.
        
        Args:
            ct_event: CloudTrail event containing the creation or acceptance response
            
        Returns:
            TGW instance
        """
        if 'AcceptTransitGatewayVpcAttachmentResponse' in ct_event.detail['responseElements']:
            resp = ct_event.detail['responseElements']['AcceptTransitGatewayVpcAttachmentResponse']['transitGatewayVpcAttachment']
            return cls(
                tgw_id=str(resp['transitGatewayId'])
            )
        elif 'CreateTransitGatewayVpcAttachmentResponse' in ct_event.detail['responseElements']:
            resp = ct_event.detail['responseElements']['CreateTransitGatewayVpcAttachmentResponse']['transitGatewayVpcAttachment']
            return cls(
                tgw_id=str(resp['transitGatewayId'])
            )
        else:
            raise ValueError("Invalid event type")
        
@dataclass
class TGWAttachment:
    """
    Represents a Transit Gateway VPC attachment.
    
    Attributes:
        account_id: AWS account ID that owns the VPC
        vpc_id: VPC identifier being attached
        attachment_id: Unique TGW attachment identifier
        state: Current state of the attachment (e.g., "pendingAcceptance", "available")
    """
    account_id: str
    vpc_id: str
    attachment_id: str
    state: str = ""
    @classmethod
    def from_event(cls, ct_event: CloudTrailEvent) -> 'TGWAttachment':
        """
        Create a TGWAttachment from a CreateTransitGatewayVpcAttachment CloudTrail event.
        
        Args:
            ct_event: CloudTrail event containing the creation response
            
        Returns:
            TGWAttachment instance
        """
        if 'AcceptTransitGatewayVpcAttachmentResponse' in ct_event.detail['responseElements']:
            resp = ct_event.detail['responseElements']['AcceptTransitGatewayVpcAttachmentResponse']['transitGatewayVpcAttachment']
            return cls(
                account_id=str(resp['vpcOwnerId']),
                vpc_id=str(resp['vpcId']),
                attachment_id=str(resp['transitGatewayAttachmentId']),
                state=str(resp.get('state', ''))
            )
        elif 'CreateTransitGatewayVpcAttachmentResponse' in ct_event.detail['responseElements']:
            resp = ct_event.detail['responseElements']['CreateTransitGatewayVpcAttachmentResponse']['transitGatewayVpcAttachment']
            return cls(
                account_id=str(resp['vpcOwnerId']),
                vpc_id=str(resp['vpcId']),
                attachment_id=str(resp['transitGatewayAttachmentId']),
                state=str(resp.get('state', ''))
            )
        else:
            raise ValueError("Invalid event type")