#!/bin/bash
# Complete AWS ECS Deployment Script

set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="your-account-id"
CLUSTER_NAME="marketing-analytics-cluster"
SERVICE_NAME="marketing-analytics-service"
TASK_DEFINITION_NAME="marketing-analytics-mcp"
ECR_REPO_NAME="marketing-analytics-mcp"

echo "🚀 Starting complete AWS deployment..."

# 1. Create ECR repository if it doesn't exist
echo "📦 Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION || \
aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION

# 2. Build and push Docker image
echo "🐳 Building and pushing Docker image..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker build -t $ECR_REPO_NAME .
docker tag $ECR_REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest

# 3. Create ECS cluster
echo "🏗️ Creating ECS cluster..."
aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION || \
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION

# 4. Register task definition
echo "📋 Registering task definition..."
# Update the task definition with your account ID
sed "s/YOUR_ACCOUNT_ID/$AWS_ACCOUNT_ID/g" cloud-deployments/aws-ecs-task-definition.json | \
aws ecs register-task-definition --region $AWS_REGION --cli-input-json file:///dev/stdin

# 5. Create or update service
echo "🚀 Creating/updating ECS service..."
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION && \
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --task-definition $TASK_DEFINITION_NAME \
  --region $AWS_REGION || \
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_DEFINITION_NAME \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}" \
  --region $AWS_REGION

echo "✅ Deployment complete!"
echo "🔍 Check service status: aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"