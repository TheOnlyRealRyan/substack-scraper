terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ECR Repository
resource "aws_ecr_repository" "substack_scraper" {
  name                 = "substack-scraper-repo"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "substack-scraper-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "substack_scraper" {
  name              = "/ecs/substack-scraper"
  retention_in_days = 30
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution_role" {
  name = "substack-scraper-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role
resource "aws_iam_role" "ecs_task_role" {
  name = "substack-scraper-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# VPC and Networking
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_security_group" "default" {
  name = "default"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "substack_scraper" {
  family                   = "substack-scraper-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "substack-scraper"
      image = "${aws_ecr_repository.substack_scraper.repository_url}:latest"
      
      essential = true
      
      environment = [
        {
          name  = "OPENROUTER_API_KEY"
          value = var.openrouter_api_key
        },
        {
          name  = "EMAIL_ADDRESS"
          value = var.email_address
        },
        {
          name  = "EMAIL_PASSWORD"
          value = var.email_password
        },
        {
          name  = "RECIPIENT_EMAIL"
          value = var.recipient_email
        }
      ]

      log_configuration = {
        log_driver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.substack_scraper.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# EventBridge Rule for 6 AM daily execution
resource "aws_cloudwatch_event_rule" "substack_scraper_schedule" {
  name                = "substack-scraper-schedule"
  description         = "Run Substack scraper daily at 6 AM UTC"
  schedule_expression = "cron(0 6 * * ? *)"
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "substack_scraper_target" {
  rule      = aws_cloudwatch_event_rule.substack_scraper_schedule.name
  target_id = "SubstackScraperTarget"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.ecs_execution_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.substack_scraper.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = data.aws_subnets.default.ids
      security_groups  = [data.aws_security_group.default.id]
      assign_public_ip = true
    }
  }
}

# Outputs
output "ecr_repository_url" {
  value = aws_ecr_repository.substack_scraper.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.substack_scraper.arn
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.substack_scraper.name
}
