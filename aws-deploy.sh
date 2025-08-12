#!/bin/bash

# AWS ECS Deployment Script for Substack Scraper
# This script sets up the infrastructure for running the scraper daily at 6 AM

set -e

# Configuration
PROJECT_NAME="substack-scraper"
REGION="us-east-1"
CLUSTER_NAME="${PROJECT_NAME}-cluster"
SERVICE_NAME="${PROJECT_NAME}-service"
TASK_DEFINITION_NAME="${PROJECT_NAME}-task"
REPOSITORY_NAME="${PROJECT_NAME}-repo"
SCHEDULE_NAME="${PROJECT_NAME}-schedule"
ROLE_NAME="${PROJECT_NAME}-execution-role"
TASK_ROLE_NAME="${PROJECT_NAME}-task-role"

echo "🚀 Starting AWS deployment for Substack Scraper..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Create ECR repository
echo "📦 Creating ECR repository..."
aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION || echo "Repository already exists"

# Get ECR repository URI
REPO_URI=$(aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $REGION --query 'repositories[0].repositoryUri' --output text)
echo "📦 ECR Repository URI: $REPO_URI"

# Build and push Docker image
echo "🐳 Building and pushing Docker image..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REPO_URI

# Build image
docker build -t $REPOSITORY_NAME .

# Tag and push
docker tag $REPOSITORY_NAME:latest $REPO_URI:latest
docker push $REPO_URI:latest

# Create execution role for ECS
echo "🔐 Creating ECS execution role..."
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}' || echo "Role already exists"

# Attach execution policy
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create task role for the application
echo "🔐 Creating task role..."
aws iam create-role --role-name $TASK_ROLE_NAME --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}' || echo "Task role already exists"

# Create ECS cluster
echo "🏗️ Creating ECS cluster..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $REGION || echo "Cluster already exists"

# Create task definition
echo "📋 Creating task definition..."
aws ecs register-task-definition --region $REGION --cli-input-json "{
  \"family\": \"$TASK_DEFINITION_NAME\",
  \"networkMode\": \"awsvpc\",
  \"requiresCompatibilities\": [\"FARGATE\"],
  \"cpu\": \"1024\",
  \"memory\": \"2048\",
  \"executionRoleArn\": \"arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/$ROLE_NAME\",
  \"taskRoleArn\": \"arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/$TASK_ROLE_NAME\",
  \"containerDefinitions\": [
    {
      \"name\": \"$PROJECT_NAME\",
      \"image\": \"$REPO_URI:latest\",
      \"essential\": true,
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"/ecs/$PROJECT_NAME\",
          \"awslogs-region\": \"$REGION\",
          \"awslogs-stream-prefix\": \"ecs\"
        }
      },
      \"environment\": [
        {
          \"name\": \"OPENROUTER_API_KEY\",
          \"value\": \"${OPENROUTER_API_KEY}\"
        },
        {
          \"name\": \"EMAIL_ADDRESS\",
          \"value\": \"${EMAIL_ADDRESS}\"
        },
        {
          \"name\": \"EMAIL_PASSWORD\",
          \"value\": \"${EMAIL_PASSWORD}\"
        },
        {
          \"name\": \"RECIPIENT_EMAIL\",
          \"value\": \"${RECIPIENT_EMAIL}\"
        }
      ]
    }
  ]
}"

# Create CloudWatch log group
echo "📝 Creating CloudWatch log group..."
aws logs create-log-group --log-group-name "/ecs/$PROJECT_NAME" --region $REGION || echo "Log group already exists"

# Create EventBridge rule for 6 AM daily execution
echo "⏰ Creating EventBridge rule for 6 AM daily execution..."
aws events put-rule \
  --name $SCHEDULE_NAME \
  --schedule-expression "cron(0 6 * * ? *)" \
  --description "Run Substack scraper daily at 6 AM UTC" \
  --region $REGION || echo "Rule already exists"

# Create EventBridge target
echo "🎯 Creating EventBridge target..."
aws events put-targets \
  --rule $SCHEDULE_NAME \
  --targets "Id"="1","Arn"="arn:aws:ecs:$REGION:$(aws sts get-caller-identity --query Account --output text):cluster/$CLUSTER_NAME","RoleArn"="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/$ROLE_NAME","EcsParameters"="{\"TaskDefinitionArn\":\"arn:aws:ecs:$REGION:$(aws sts get-caller-identity --query Account --output text):task-definition/$TASK_DEFINITION_NAME\",\"LaunchType\":\"FARGATE\",\"NetworkConfiguration\":{\"awsvpcConfiguration\":{\"Subnets\":[\"$(aws ec2 describe-subnets --region $REGION --query 'Subnets[0].SubnetId' --output text)\"],\"SecurityGroups\":[\"$(aws ec2 describe-security-groups --region $REGION --query 'SecurityGroups[0].GroupId' --output text)\"],\"AssignPublicIp\":\"ENABLED\"}}}" \
  --region $REGION || echo "Target already exists"

# Create security group for ECS tasks
echo "🔒 Creating security group..."
aws ec2 create-security-group \
  --group-name "${PROJECT_NAME}-sg" \
  --description "Security group for Substack scraper ECS tasks" \
  --region $REGION || echo "Security group already exists"

SG_ID=$(aws ec2 describe-security-groups --group-names "${PROJECT_NAME}-sg" --region $REGION --query 'SecurityGroups[0].GroupId' --output text)

# Add outbound rule
aws ec2 authorize-security-group-egress \
  --group-id $SG_ID \
  --protocol -1 \
  --port -1 \
  --cidr 0.0.0.0/0 \
  --region $REGION || echo "Outbound rule already exists"

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Summary:"
echo "   ECS Cluster: $CLUSTER_NAME"
echo "   Task Definition: $TASK_DEFINITION_NAME"
echo "   ECR Repository: $REPO_URI"
echo "   Schedule: Daily at 6 AM UTC"
echo "   Log Group: /ecs/$PROJECT_NAME"
echo ""
echo "🔍 To monitor execution:"
echo "   aws logs tail /ecs/$PROJECT_NAME --follow --region $REGION"
echo ""
echo "🚀 To run manually:"
echo "   aws ecs run-task --cluster $CLUSTER_NAME --task-definition $TASK_DEFINITION_NAME --region $REGION"
echo ""
echo "📊 To view execution history:"
echo "   aws events list-targets-by-rule --rule $SCHEDULE_NAME --region $REGION"
