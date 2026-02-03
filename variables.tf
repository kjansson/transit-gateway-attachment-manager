variable "additional_ipam_regions" {
  description = "Additional regions for IPAM to monitor (beyond current region)"
  type        = list(string)
  default     = []
}

variable "environment" {
  type        = string
  description = "The environment for the resources"
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "function_timeout" {
  description = "Default timeout for all Lambda functions in seconds"
  type        = number
  default     = 60
}

variable "function_memory_size" {
  description = "Memory allocation for the Lambda function in MB"
  type        = number
  default     = 128
}

variable "log_group_retention_days" {
  description = "Retention period for the CloudWatch log group in days"
  type        = number
  default     = 365
}

variable "log_group_class" {
  description = "Class of the CloudWatch Logs log group"
  type        = string
  default     = "STANDARD"
}

variable "additional_tags" {
  description = "Additional tags to be applied to the resources"
  type        = map(string)
  default     = {}
}
variable "allowed_principal_patterns" {
  description = "A string list of allowed principal patterns for the Lambda function"
  type        = list(string)
  default     = []
}

variable "default_associate_route_table_id" {
  description = "A Transit Gateway route table ID to associate attachments with if no tag match is found on pool or IPAM is not used."
  type        = string
  default     = ""
}

variable "default_propagate_route_table_ids" {
  description = "Comma separated list of Transit Gateway route table IDs to enable propagation for attachments: eg. 'rtb-12345678,rtb-87654321'. Used if no tag match is found on pool or IPAM is not used."
  type        = string
  default     = ""
}

variable "log_level" {
  description = "Log level for the Lambda function"
  type        = string
  default     = "DEBUG"
}

variable "ipam_pool_ids" {
  description = "The IPAM Pool ID for the resources"
  type        = list(string)
  default     = []
}

variable "tgwa_additional_tag_key" {
  description = "Additional tag key to be added to the TGW attachment"
  type        = string
  default     = ""
}

variable "tgwa_additional_tag_value" {
  description = "Additional tag value to be added to the TGW attachment"
  type        = string
  default     = ""
}
variable "ipam_association_tag_key" {
  description = "Tag key to retrieve association route table ID from the IPAM pool"
  type        = string
  default     = ""
}

variable "ipam_propagation_tag_key" {
  description = "Tag key to retrieve propagation route table IDs from the IPAM pool"
  type        = string
  default     = ""
}

variable "attachment_tag_key" {
  description = "Tag key to retrieve additional tag key for the TGW attachment"
  type        = string
  default     = ""
}
variable "attachment_tag_value" {
  description = "Tag key to retrieve additional tag value for the TGW attachment"
  type        = string
  default     = ""
}

variable "approval_email_addresses" {
  description = "Comma-separated list of email addresses for approval notifications. Will create a SNS subscription for each email address provided."
  type        = string
  default     = ""
}