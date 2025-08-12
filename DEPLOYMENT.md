# AWS Deployment Guide

This guide walks you through deploying the Substack Scraper to AWS with scheduled execution at 6 AM daily.

## Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Installed and configured with your credentials
3. **Docker**: Installed and running locally
4. **API Keys**: OpenRouter API key and Gmail credentials

## Quick Deployment (Recommended)

### 1. Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, region, and output format
```

### 2. Set Environment Variables

```bash
export OPENROUTER_API_KEY="your_openrouter_api_key"
export EMAIL_ADDRESS="your_gmail_address"
export EMAIL_PASSWORD="your_gmail_app_password"
export RECIPIENT_EMAIL="recipient@example.com"
```

**Important**: Use Gmail App Password, not your regular password. [Learn how to create one](https://support.google.com/accounts/answer/185833).

### 3. Run Deployment Script

```bash
chmod +x aws-deploy.sh
./aws-deploy.sh
```

The script will:
- Create ECR repository for Docker images
- Build and push your Docker image
- Create ECS cluster and task definition
- Set up EventBridge rule for 6 AM daily execution
- Configure IAM roles and security groups
- Set up CloudWatch logging

### 4. Verify Deployment

```bash
# Check ECS cluster
aws ecs describe-clusters --clusters substack-scraper-cluster

# Check EventBridge rule
aws events describe-rule --name substack-scraper-schedule

# View logs
aws logs tail /ecs/substack-scraper --follow
```

## Manual Deployment with Terraform

### 1. Navigate to Terraform Directory

```bash
cd terraform
```

### 2. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### 4. Build and Push Docker Image

```bash
# Get ECR repository URL from terraform output
ECR_URL=$(terraform output -raw ecr_repository_url)

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL

# Build and push
docker build -t substack-scraper .
docker tag substack-scraper:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

## Infrastructure Components

### ECS (Elastic Container Service)
- **Cluster**: Manages container execution
- **Task Definition**: Defines how containers run
- **Fargate**: Serverless container execution (pay-per-use)

### ECR (Elastic Container Registry)
- **Repository**: Stores Docker images
- **Image Scanning**: Automatic security scanning
- **Lifecycle Policies**: Automatic cleanup of old images

### EventBridge
- **Rule**: Scheduled execution at 6 AM UTC daily
- **Target**: Triggers ECS task execution
- **Cron Expression**: `cron(0 6 * * ? *)`

### CloudWatch
- **Log Group**: Centralized logging for containers
- **Log Retention**: 30 days (configurable)
- **Monitoring**: Container insights and metrics

### IAM (Identity and Access Management)
- **Execution Role**: Allows ECS to pull images and write logs
- **Task Role**: Permissions for your application
- **Least Privilege**: Minimal required permissions

## Cost Estimation

### Free Tier (First 12 months)
- **ECR**: 500 MB storage/month
- **ECS Fargate**: 2,000 seconds/month
- **EventBridge**: 1,000,000 events/month
- **CloudWatch**: 5 GB log ingestion/month

### Pay-as-you-use (After free tier)
- **ECS Fargate**: ~$0.04 per vCPU hour + $0.004 per GB hour
- **ECR**: $0.10 per GB per month
- **EventBridge**: $1.00 per million events
- **CloudWatch**: $0.50 per GB ingested

**Estimated monthly cost**: $2-5 (depending on execution time)

## Monitoring and Maintenance

### View Logs

```bash
# Real-time logs
aws logs tail /ecs/substack-scraper --follow

# Recent logs
aws logs describe-log-streams --log-group-name /ecs/substack-scraper --order-by LastEventTime --descending --max-items 5
```

### Check Execution Status

```bash
# View EventBridge rule
aws events describe-rule --name substack-scraper-schedule

# Check recent executions
aws events list-targets-by-rule --rule substack-scraper-schedule
```

### Manual Execution

```bash
# Run task manually
aws ecs run-task \
  --cluster substack-scraper-cluster \
  --task-definition substack-scraper-task \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

### Update Application

```bash
# Build new image
docker build -t substack-scraper .

# Tag and push
docker tag substack-scraper:latest $ECR_URL:latest
docker push $ECR_URL:latest

# Update task definition (ECS will use latest image automatically)
```

## Troubleshooting

### Common Issues

1. **Task fails to start**
   - Check IAM role permissions
   - Verify environment variables
   - Check CloudWatch logs

2. **Container crashes**
   - Review application logs
   - Check resource limits (CPU/Memory)
   - Verify API keys and credentials

3. **Scheduled execution not working**
   - Verify EventBridge rule exists
   - Check IAM permissions for EventBridge
   - Verify target configuration

4. **Email not sending**
   - Check Gmail credentials
   - Verify SMTP settings
   - Check network connectivity

### Debug Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster substack-scraper-cluster --services substack-scraper-service

# View task definition
aws ecs describe-task-definition --task-definition substack-scraper-task

# Check IAM roles
aws iam get-role --role-name substack-scraper-execution-role
aws iam get-role --role-name substack-scraper-task-role

# View security groups
aws ec2 describe-security-groups --group-names substack-scraper-sg
```

## Security Considerations

### Network Security
- **VPC**: Default VPC with public subnets
- **Security Groups**: Minimal required access
- **No Inbound Rules**: Only outbound internet access

### Data Security
- **Environment Variables**: Sensitive data encrypted in transit
- **IAM Roles**: Least privilege access
- **Container Security**: Non-root user execution

### Monitoring
- **CloudWatch Logs**: Centralized logging
- **Container Insights**: Performance monitoring
- **IAM Access Analyzer**: Permission auditing

## Scaling and Optimization

### Performance Tuning
- **CPU/Memory**: Adjust based on workload
- **Concurrency**: Process multiple articles simultaneously
- **Timeout Settings**: Optimize for network conditions

### Cost Optimization
- **Spot Instances**: Use for non-critical workloads
- **Reserved Capacity**: For predictable usage patterns
- **Lifecycle Policies**: Automatic cleanup of old resources

### High Availability
- **Multi-AZ**: Deploy across availability zones
- **Auto-scaling**: Scale based on demand
- **Health Checks**: Monitor application health

## Support and Resources

### AWS Documentation
- [ECS User Guide](https://docs.aws.amazon.com/ecs/)
- [EventBridge User Guide](https://docs.aws.amazon.com/eventbridge/)
- [CloudWatch User Guide](https://docs.aws.amazon.com/cloudwatch/)

### Troubleshooting
- [AWS Support Center](https://console.aws.amazon.com/support/)
- [AWS Forums](https://forums.aws.amazon.com/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/amazon-web-services)

### Community
- [GitHub Issues](https://github.com/your-repo/substack-scraper/issues)
- [Discussions](https://github.com/your-repo/substack-scraper/discussions)
