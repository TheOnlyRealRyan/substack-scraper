# Substack AI Article Scraper

A comprehensive tool that scrapes AI-related articles from Substack, generates AI-powered summaries, and sends daily digest emails. Now with SQLite database storage and AWS deployment capabilities.

## Features

- **Web Scraping**: Automatically scrapes AI articles from Substack search results
- **AI Summarization**: Uses OpenRouter API to generate intelligent summaries
- **Database Storage**: SQLite database for persistent data storage
- **Email Delivery**: Daily digest emails with formatted summaries
- **AWS Deployment**: Containerized deployment with scheduled execution
- **Monitoring**: Comprehensive logging and execution tracking

## Architecture

The application has been refactored into a single, cohesive pipeline:

1. **Scraping**: Extracts article content from Substack
2. **Storage**: Saves articles and metadata to SQLite database
3. **Summarization**: Generates AI summaries for new articles
4. **Email**: Sends daily digest with today's summaries
5. **Logging**: Tracks all execution metrics and errors

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for containerized deployment)
- AWS CLI (for AWS deployment)
- OpenRouter API key
- Gmail credentials

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd substack-scraper
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   playwright install-deps
   ```

3. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your API keys and email credentials
   ```

4. **Run locally**:
   ```bash
   python substack_scraper.py
   ```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t substack-scraper .
docker run --env-file .env substack-scraper
```

## AWS Deployment

### Option 1: Automated Script (Recommended)

1. **Configure AWS CLI**:
   ```bash
   aws configure
   ```

2. **Set environment variables**:
   ```bash
   export OPENROUTER_API_KEY="your_key"
   export EMAIL_ADDRESS="your_email"
   export EMAIL_PASSWORD="your_password"
   export RECIPIENT_EMAIL="recipient@example.com"
   ```

3. **Run deployment script**:
   ```bash
   chmod +x aws-deploy.sh
   ./aws-deploy.sh
   ```

### Option 2: Terraform (Infrastructure as Code)

1. **Navigate to terraform directory**:
   ```bash
   cd terraform
   ```

2. **Configure variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Deploy infrastructure**:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

4. **Build and push Docker image**:
   ```bash
   # Get ECR repository URL from terraform output
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ecr-url>
   docker build -t substack-scraper .
   docker tag substack-scraper:latest <ecr-url>:latest
   docker push <ecr-url>:latest
   ```

## Configuration

### Environment Variables

- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `EMAIL_ADDRESS`: Gmail address for sending emails
- `EMAIL_PASSWORD`: Gmail app password (not regular password)
- `RECIPIENT_EMAIL`: Email address to receive summaries

### Database

The SQLite database (`substack_articles.db`) contains:
- **articles**: Scraped article content and metadata
- **summaries**: AI-generated summaries linked to articles
- **execution_logs**: Pipeline execution history and metrics

### Scheduling

The application runs automatically at **6 AM UTC daily** when deployed on AWS. You can modify the schedule in:
- `aws-deploy.sh`: Line with `cron(0 6 * * ? *)`
- `terraform/main.tf`: EventBridge rule configuration

## Monitoring

### CloudWatch Logs

View execution logs in AWS CloudWatch:
```bash
aws logs tail /ecs/substack-scraper --follow --region us-east-1
```

### Local Logs

Check local execution logs:
```bash
tail -f substack_scraper.log
```

### Database Queries

Monitor database activity:
```bash
sqlite3 substack_articles.db
.tables
SELECT * FROM execution_logs ORDER BY created_at DESC LIMIT 5;
```

## Manual Execution

### AWS ECS

```bash
aws ecs run-task \
  --cluster substack-scraper-cluster \
  --task-definition substack-scraper-task \
  --region us-east-1
```

### Local

```bash
python substack_scraper.py
```

## Troubleshooting

### Common Issues

1. **Playwright browser issues**: Ensure system dependencies are installed
2. **Email authentication**: Use Gmail App Password, not regular password
3. **API rate limits**: OpenRouter has usage limits; check your plan
4. **AWS permissions**: Ensure IAM roles have necessary permissions

### Debug Mode

Enable verbose logging by modifying the logging level in `substack_scraper.py`:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Cost Optimization

- **ECS Fargate**: Pay-per-use container execution
- **EventBridge**: Free tier includes 1M events/month
- **CloudWatch**: Free tier includes 5GB log ingestion/month
- **ECR**: Free tier includes 500MB storage/month

## Security

- **Environment variables**: Sensitive data stored securely
- **IAM roles**: Minimal required permissions
- **Container security**: Non-root user execution
- **Network isolation**: VPC and security group configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.