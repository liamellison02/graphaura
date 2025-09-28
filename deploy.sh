#!/bin/bash

# GraphAura Production Deployment Script

set -e

echo "🚀 GraphAura Production Deployment"
echo "=================================="

# Check for required environment variables
if [ ! -f .env.production ]; then
    echo "❌ .env.production file not found!"
    echo "Please copy .env.production.example to .env.production and configure it."
    exit 1
fi

# Load environment variables
export $(cat .env.production | grep -v '^#' | xargs)

# Function to deploy to different platforms
deploy_railway() {
    echo "📦 Deploying to Railway..."
    cd backend
    railway up
    cd ..
}

deploy_render() {
    echo "📦 Deploying to Render..."
    # Render deployment via blueprint
    echo "Please ensure render.yaml is configured and push to GitHub"
}

deploy_docker() {
    echo "🐳 Deploying with Docker Compose..."
    docker-compose -f docker-compose.production.yml up -d --build
}

deploy_kubernetes() {
    echo "☸️ Deploying to Kubernetes..."
    kubectl apply -f k8s/
}

# Main menu
echo "Select deployment method:"
echo "1) Railway (Recommended for backend)"
echo "2) Render"
echo "3) Docker Compose (VPS/Self-hosted)"
echo "4) Kubernetes"
echo "5) Full Stack Setup Guide"

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        deploy_railway
        ;;
    2)
        deploy_render
        ;;
    3)
        deploy_docker
        ;;
    4)
        deploy_kubernetes
        ;;
    5)
        echo "Opening deployment guide..."
        cat DEPLOYMENT.md
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo "✅ Deployment initiated!"