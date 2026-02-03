# Transit Gateway Attachment Manager

This Terraform module automates the acceptance of Transit Gateway VPC attachments in AWS using Eventbridge and Step Functions.  

## Features
- Automatically accepts Transit Gateway VPC attachments without using the limitations of the native TGW auto-accept feature.
- Creates optional guardrails for acceptance based on AWS IPAM pools, IAM principals and manual approval workflows.
- Enables automatic and dynamic route propagation to multiple routing domains.
- Automatic tagging of attachments upon acceptance.

## Why?
The native attachment sequence (automatic and manual) in Transit Gateway has several limitations;

<ol>
<li>The auto-accept attachment feature in TGW gives up too much control over who can attach. You are left relying on who you share your TGW with and trusting that the connecting VPCs are actually correctly configured.</li>
<li>Using auto-accept effectively limits you to one routing domain, with all attachments associating and propagating to the same route tables.</li>
<li>Using the manual attachment sequence does not work well with a IaC/Gitops approach since it requires changes in multiple accounts, and lacks good notification options for being alerted to new attachment requests.</li>
</ol>

This module aims to extend and automate the attachment acceptance sequence but with built in guardrails for who and what is allowed to attach, and what routing domain they should belong to. 

## Design

The Attachment Manager runs as two Step Function state machines responsible for managing the accepting automation and guardrails, and the routing management for an newly accepted attachment.  

The components of the Step Functions are 100% configurable and can be enabled/disabled depending on your needs.

### Accepter

The Accepter step function triggers on the event produced by a TGW attachment requesting attachment to the Transit Gateway.  
In its default low/no configuration mode, it will simply accept the attachment, but optional guardrails before acceptance can be enabled;

<ul>
<li>IAM validation: validate the requesting identitity. Allowed IAM principals can be limited by name patterns. Usage example;</li>
<ul>
<li>Limit attachment requests to roles used in IaC workflows.</li>
<li>Limit attachment requests to network admin roles.</li>
</ul>
<li>AWS IPAM validation: validate that the requesting VPC has a CIDR range allocated by a specific AWS IPAM pool. Usage example;</li> 
<ul>
<li>Prevent VPC from requesting attachment to Transit Gateways in other environments or network segments.</li>
<li>Prevent CIDR range overlap from attachments with CIDR ranges not managed in IPAM.</li>
</ul>
<li>Manual approval: human interaction. Implemented via SNS with email and approval link as default, but integration to Slack, Teams etc is supported by SNS.</li>
</ul>

![Accepter](/img/accepter.png)

### Routing manager

The Routing Manager step function manages the TGW route table association and propagation(s) after an attachment has been accepted.  
Unlike the native auto-accept functionality in TGW, the Routing Manager can be configured to propagate attachments to multiple route tables, possibly creating multiple routing domains.  
When used with AWS IPAM it can even dynamically manage association and propagation using tags on your IPAM pools.  
This makes it possible to automate the separation of VPCs on a routing level within the same TGW.  
As an example, VPCs using to a non-prod IPAM pool can associate and propagate to a non-prod routing domain, separated from VPCs using a production pool.

![Routing Manager](/img/routing.png)# transit-gateway-attachment-manager
