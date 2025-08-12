variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "openrouter_api_key" {
  description = "OpenRouter API key for AI summarization"
  type        = string
  sensitive   = true
}

variable "email_address" {
  description = "Email address for sending summaries"
  type        = string
  sensitive   = true
}

variable "email_password" {
  description = "Email password for sending summaries"
  type        = string
  sensitive   = true
}

variable "recipient_email" {
  description = "Recipient email address for summaries"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "substack-scraper"
}
