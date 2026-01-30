# FortiGate AWS HA Deployment - Streamlit Web Application Guide

## Overview

This guide provides comprehensive instructions for deploying, configuring, and operating the Streamlit web application for FortiGate AWS HA deployments. The web application provides an intuitive graphical interface for managing FortiGate deployments with real-time progress tracking and cost analysis.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Deployment Options](#deployment-options)
5. [Security Configuration](#security-configuration)
6. [Operation and Monitoring](#operation-and-monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Scaling and Load Balancing](#scaling-and-load-balancing)

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **Memory**: Minimum 2GB RAM, recommended 4GB+
- **Storage**: 1GB free space for application and dependencies
- **Network**: Internet access for AWS API calls and package downloads

### AWS Requirements

- Valid AWS credentials with appropriate permissions
- Access to target AWS regions for FortiGate deployment
- VPC and networking infrastructure pre-configured by network team

### Dependencies

The application requires the following Python packages:
- `streamlit >= 1.28.0`
- `boto3 >= 1.26.0`
- `pandas >= 1.5.0`
- `plotly >= 5.15.0`
- `pyyaml >= 6.0`
- `click >= 8.0.0`

## Installation

### Option 1: Local Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd fortigate-aws-ha-deployment
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Verify installation:**
```bash
streamlit --version
python -c "import boto3; print('AWS SDK installed successfully')"
```

### Option 2: Docker Installation

1. **Create Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run Streamlit
CMD ["streamlit", "run", "web-app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. **Build Docker image:**
```bash
docker build -t fortigate-streamlit-app .
```

3. **Run container:**
```bash
docker run -p 8501:8501 \
  -e AWS_ACCESS_KEY_ID=your_access_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret_key \
  -e AWS_DEFAULT_REGION=us-east-1 \
  fortigate-streamlit-app
```

### Option 3: Cloud Deployment (AWS ECS)

1. **Create ECS task definition:**
```json
{
  "family": "fortigate-streamlit-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/fortigate-deployment-role",
  "containerDefinitions": [
    {
      "name": "streamlit-app",
      "image": "your-account.dkr.ecr.region.amazonaws.com/fortigate-streamlit-app:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_DEFAULT_REGION",
          "value": "us-east-1"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/fortigate-streamlit-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# AWS Configuration
AWS_DEFAULT_REGION=us-east-1
AWS_PROFILE=default  # Optional if using IAM roles

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Application Configuration
FORTIGATE_DEFAULT_VERSION=7.4
FORTIGATE_DEFAULT_INSTANCE_TYPE=c5.xlarge
DEPLOYMENT_TIMEOUT=3600  # seconds

# Security Configuration
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
```

### Streamlit Configuration File

Create `.streamlit/config.toml`:

```toml
[server]
port = 8501
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B35"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[logger]
level = "info"
```

### AWS Credentials Configuration

#### Option 1: AWS Profile
```bash
aws configure --profile fortigate-deployment
# Enter your AWS Access Key ID, Secret Access Key, and region
```

#### Option 2: IAM Role (Recommended for production)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "iam:PassRole",
        "secretsmanager:GetSecretValue",
        "s3:GetObject",
        "pricing:GetProducts"
      ],
      "Resource": "*"
    }
  ]
}
```

## Deployment Options

### Local Development

1. **Start the application:**
```bash
streamlit run web-app.py
```

2. **Access the application:**
Open your browser to `http://localhost:8501`

3. **Development mode with auto-reload:**
```bash
streamlit run web-app.py --server.runOnSave=true
```

### Production Deployment

#### Using systemd (Linux)

1. **Create service file `/etc/systemd/system/fortigate-streamlit.service`:**
```ini
[Unit]
Description=FortiGate Streamlit Web Application
After=network.target

[Service]
Type=simple
User=streamlit
WorkingDirectory=/opt/fortigate-aws-ha-deployment
Environment=PATH=/opt/fortigate-aws-ha-deployment/venv/bin
ExecStart=/opt/fortigate-aws-ha-deployment/venv/bin/streamlit run web-app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **Enable and start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable fortigate-streamlit
sudo systemctl start fortigate-streamlit
```

#### Using Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  fortigate-streamlit:
    build: .
    ports:
      - "8501:8501"
    environment:
      - AWS_DEFAULT_REGION=us-east-1
    volumes:
      - ~/.aws:/root/.aws:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Start with:
```bash
docker-compose up -d
```

## Security Configuration

### Authentication Setup

#### Option 1: Basic Authentication (Development)

Add to your Streamlit app:
```python
import streamlit as st

def check_password():
    def password_entered():
        if st.session_state["password"] == "your_secure_password":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()
```

#### Option 2: OAuth Integration (Production)

Use `streamlit-authenticator` package:
```python
import streamlit_authenticator as stauth

# Configuration
config = {
    'credentials': {
        'usernames': {
            'admin': {
                'name': 'Administrator',
                'password': 'hashed_password',
                'email': 'admin@company.com'
            }
        }
    },
    'cookie': {
        'name': 'fortigate_auth_cookie',
        'key': 'random_signature_key',
        'expiry_days': 30
    }
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, authentication_status, username = authenticator.login('Login', 'main')
```

### HTTPS Configuration

#### Using Nginx Reverse Proxy

1. **Install Nginx:**
```bash
sudo apt update
sudo apt install nginx
```

2. **Create Nginx configuration `/etc/nginx/sites-available/fortigate-streamlit`:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/fortigate-streamlit /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Network Security

#### Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

#### VPC Security Groups (AWS)

```json
{
  "GroupName": "fortigate-streamlit-sg",
  "Description": "Security group for FortiGate Streamlit application",
  "SecurityGroupRules": [
    {
      "IpProtocol": "tcp",
      "FromPort": 443,
      "ToPort": 443,
      "CidrIp": "10.0.0.0/8",
      "Description": "HTTPS access from corporate network"
    },
    {
      "IpProtocol": "tcp",
      "FromPort": 22,
      "ToPort": 22,
      "CidrIp": "10.0.0.0/8",
      "Description": "SSH access for management"
    }
  ]
}
```

## Operation and Monitoring

### Health Checks

The application provides several health check endpoints:

1. **Streamlit health check:**
```bash
curl http://localhost:8501/_stcore/health
```

2. **Application-specific health check:**
```python
# Add to your Streamlit app
def health_check():
    try:
        # Test AWS connectivity
        import boto3
        ec2 = boto3.client('ec2')
        ec2.describe_regions()
        return True
    except Exception as e:
        st.error(f"Health check failed: {e}")
        return False
```

### Logging Configuration

#### Application Logs

Configure logging in your Streamlit app:
```python
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/fortigate-streamlit.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
```

#### System Logs

Monitor system logs:
```bash
# Systemd service logs
sudo journalctl -u fortigate-streamlit -f

# Application logs
tail -f /var/log/fortigate-streamlit.log

# Nginx logs (if using reverse proxy)
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Performance Monitoring

#### Resource Usage

Monitor system resources:
```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Network connections
netstat -tulpn | grep :8501
```

#### Application Metrics

Add metrics to your Streamlit app:
```python
import time
import psutil
import streamlit as st

def display_system_metrics():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        cpu_percent = psutil.cpu_percent()
        st.metric("CPU Usage", f"{cpu_percent}%")
    
    with col2:
        memory = psutil.virtual_memory()
        st.metric("Memory Usage", f"{memory.percent}%")
    
    with col3:
        disk = psutil.disk_usage('/')
        st.metric("Disk Usage", f"{disk.percent}%")
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms:**
- Error: "ModuleNotFoundError"
- Error: "Permission denied"

**Solutions:**
```bash
# Check Python version
python --version

# Verify virtual environment
which python
which pip

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check permissions
ls -la web-app.py
chmod +x web-app.py
```

#### 2. AWS Connection Issues

**Symptoms:**
- Error: "Unable to locate credentials"
- Error: "Access denied"

**Solutions:**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check AWS configuration
aws configure list

# Test AWS connectivity
aws ec2 describe-regions --region us-east-1
```

#### 3. Port Already in Use

**Symptoms:**
- Error: "Address already in use"

**Solutions:**
```bash
# Find process using port 8501
sudo lsof -i :8501

# Kill process if necessary
sudo kill -9 <PID>

# Use different port
streamlit run web-app.py --server.port=8502
```

#### 4. Memory Issues

**Symptoms:**
- Application becomes slow or unresponsive
- Out of memory errors

**Solutions:**
```bash
# Check memory usage
free -h

# Restart application
sudo systemctl restart fortigate-streamlit

# Increase system memory or optimize code
```

### Debug Mode

Enable debug mode for troubleshooting:
```bash
# Set debug environment variables
export STREAMLIT_LOGGER_LEVEL=debug
export PYTHONPATH=/path/to/your/app

# Run with verbose output
streamlit run web-app.py --logger.level=debug
```

### Log Analysis

Common log patterns to look for:

```bash
# Successful startup
grep "You can now view your Streamlit app" /var/log/fortigate-streamlit.log

# AWS API errors
grep "ClientError\|BotoCoreError" /var/log/fortigate-streamlit.log

# Authentication failures
grep "authentication\|login" /var/log/fortigate-streamlit.log

# Performance issues
grep "timeout\|slow" /var/log/fortigate-streamlit.log
```

## Scaling and Load Balancing

### Horizontal Scaling

#### Using Docker Swarm

1. **Create Docker Swarm service:**
```bash
docker service create \
  --name fortigate-streamlit \
  --replicas 3 \
  --publish 8501:8501 \
  --env AWS_DEFAULT_REGION=us-east-1 \
  fortigate-streamlit-app
```

2. **Scale service:**
```bash
docker service scale fortigate-streamlit=5
```

#### Using Kubernetes

1. **Create deployment manifest:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fortigate-streamlit
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fortigate-streamlit
  template:
    metadata:
      labels:
        app: fortigate-streamlit
    spec:
      containers:
      - name: streamlit-app
        image: fortigate-streamlit-app:latest
        ports:
        - containerPort: 8501
        env:
        - name: AWS_DEFAULT_REGION
          value: "us-east-1"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: fortigate-streamlit-service
spec:
  selector:
    app: fortigate-streamlit
  ports:
  - port: 80
    targetPort: 8501
  type: LoadBalancer
```

### Load Balancing

#### Application Load Balancer (AWS)

1. **Create target group:**
```bash
aws elbv2 create-target-group \
  --name fortigate-streamlit-targets \
  --protocol HTTP \
  --port 8501 \
  --vpc-id vpc-12345678 \
  --health-check-path /_stcore/health
```

2. **Create load balancer:**
```bash
aws elbv2 create-load-balancer \
  --name fortigate-streamlit-alb \
  --subnets subnet-12345678 subnet-87654321 \
  --security-groups sg-12345678
```

#### Session Affinity

For stateful applications, configure session affinity:
```python
# Add session state management
import streamlit as st

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# Store session data in external store (Redis, DynamoDB)
def save_session_data(user_id, data):
    # Implementation depends on your chosen storage
    pass
```

### Performance Optimization

#### Caching

Implement caching for expensive operations:
```python
import streamlit as st

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_ami_list(region, version):
    # Expensive AMI discovery operation
    return ami_discovery.list_amis(region, version)

@st.cache_resource
def get_aws_session():
    # Cache AWS session
    return boto3.Session()
```

#### Resource Limits

Configure resource limits:
```python
# Limit concurrent operations
import asyncio
semaphore = asyncio.Semaphore(5)

async def limited_operation():
    async with semaphore:
        # Perform operation
        pass
```

## Maintenance

### Regular Maintenance Tasks

1. **Update dependencies:**
```bash
pip list --outdated
pip install --upgrade streamlit boto3
```

2. **Log rotation:**
```bash
# Configure logrotate
sudo nano /etc/logrotate.d/fortigate-streamlit
```

3. **Security updates:**
```bash
sudo apt update && sudo apt upgrade
```

4. **Backup configuration:**
```bash
tar -czf fortigate-streamlit-backup-$(date +%Y%m%d).tar.gz \
  /opt/fortigate-aws-ha-deployment
```

### Monitoring and Alerting

Set up monitoring for:
- Application availability
- Response time
- Error rates
- Resource usage
- AWS API quotas

Example CloudWatch alarm:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "FortiGate-Streamlit-High-CPU" \
  --alarm-description "High CPU usage on Streamlit app" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

## Support and Resources

- **Application Logs**: `/var/log/fortigate-streamlit.log`
- **Configuration**: `.streamlit/config.toml`
- **Health Check**: `http://localhost:8501/_stcore/health`
- **Streamlit Documentation**: https://docs.streamlit.io/
- **AWS SDK Documentation**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

For additional support, check the troubleshooting section or contact your system administrator.