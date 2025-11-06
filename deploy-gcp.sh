#!/bin/bash
#
# Deploy Single-User Trading Bot to GCP Cloud Run
#
# Prerequisites:
# 1. gcloud CLI installed and authenticated
# 2. Docker installed
# 3. GCP project created
# 4. Billing enabled
# 5. Cloud Run API enabled
# 6. Secret Manager API enabled
#
# Usage:
#   ./deploy-gcp.sh

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="us-east4"  # Ashburn, VA (co-located with Coinbase)
SERVICE_NAME="coinswarm-bot"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Check gcloud auth
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi

    # Set project
    log_info "Setting GCP project: ${PROJECT_ID}"
    gcloud config set project "${PROJECT_ID}"

    log_info "Prerequisites OK"
}

enable_apis() {
    log_info "Enabling required GCP APIs..."

    gcloud services enable \
        run.googleapis.com \
        containerregistry.googleapis.com \
        secretmanager.googleapis.com \
        --quiet

    log_info "APIs enabled"
}

create_secrets() {
    log_info "Creating secrets in Secret Manager..."

    # Check if secrets already exist
    if gcloud secrets describe cosmos-endpoint &> /dev/null; then
        log_warn "Secret cosmos-endpoint already exists. Skipping..."
    else
        # Prompt for Azure Cosmos DB endpoint
        echo -n "Enter Azure Cosmos DB endpoint: "
        read -r COSMOS_ENDPOINT
        echo -n "${COSMOS_ENDPOINT}" | gcloud secrets create cosmos-endpoint \
            --data-file=- \
            --replication-policy="automatic"
    fi

    if gcloud secrets describe cosmos-key &> /dev/null; then
        log_warn "Secret cosmos-key already exists. Skipping..."
    else
        # Prompt for Azure Cosmos DB key
        echo -n "Enter Azure Cosmos DB key: "
        read -rs COSMOS_KEY
        echo
        echo -n "${COSMOS_KEY}" | gcloud secrets create cosmos-key \
            --data-file=- \
            --replication-policy="automatic"
    fi

    if gcloud secrets describe coinbase-api-key &> /dev/null; then
        log_warn "Secret coinbase-api-key already exists. Skipping..."
    else
        # Prompt for Coinbase API key
        echo -n "Enter Coinbase API key: "
        read -r COINBASE_API_KEY
        echo -n "${COINBASE_API_KEY}" | gcloud secrets create coinbase-api-key \
            --data-file=- \
            --replication-policy="automatic"
    fi

    if gcloud secrets describe coinbase-api-secret &> /dev/null; then
        log_warn "Secret coinbase-api-secret already exists. Skipping..."
    else
        # Prompt for Coinbase API secret
        echo -n "Enter Coinbase API secret: "
        read -rs COINBASE_API_SECRET
        echo
        echo -n "${COINBASE_API_SECRET}" | gcloud secrets create coinbase-api-secret \
            --data-file=- \
            --replication-policy="automatic"
    fi

    log_info "Secrets created"
}

create_service_account() {
    log_info "Creating service account..."

    SA_NAME="coinswarm-bot"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

    # Check if service account exists
    if gcloud iam service-accounts describe "${SA_EMAIL}" &> /dev/null; then
        log_warn "Service account ${SA_EMAIL} already exists. Skipping..."
    else
        gcloud iam service-accounts create "${SA_NAME}" \
            --display-name="Coinswarm Trading Bot" \
            --description="Service account for single-user trading bot"
    fi

    # Grant permissions
    log_info "Granting Secret Manager access..."
    gcloud secrets add-iam-policy-binding cosmos-endpoint \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet || true

    gcloud secrets add-iam-policy-binding cosmos-key \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet || true

    gcloud secrets add-iam-policy-binding coinbase-api-key \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet || true

    gcloud secrets add-iam-policy-binding coinbase-api-secret \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet || true

    log_info "Service account configured"
}

build_image() {
    log_info "Building Docker image..."

    docker build \
        -f Dockerfile.single-user \
        -t "${IMAGE_NAME}:latest" \
        -t "${IMAGE_NAME}:$(git rev-parse --short HEAD)" \
        .

    log_info "Docker image built: ${IMAGE_NAME}:latest"
}

push_image() {
    log_info "Pushing Docker image to GCR..."

    # Configure Docker auth
    gcloud auth configure-docker --quiet

    # Push image
    docker push "${IMAGE_NAME}:latest"
    docker push "${IMAGE_NAME}:$(git rev-parse --short HEAD)"

    log_info "Docker image pushed"
}

deploy_cloud_run() {
    log_info "Deploying to Cloud Run..."

    # Update cloud-run.yaml with project ID
    sed -i.bak "s/YOUR_PROJECT_ID/${PROJECT_ID}/g" cloud-run.yaml

    # Deploy
    gcloud run services replace cloud-run.yaml \
        --region="${REGION}" \
        --quiet

    # Restore original file
    mv cloud-run.yaml.bak cloud-run.yaml

    log_info "Deployed to Cloud Run"
}

get_service_url() {
    log_info "Getting service URL..."

    SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
        --region="${REGION}" \
        --format="value(status.url)")

    log_info "Service URL: ${SERVICE_URL}"
}

test_deployment() {
    log_info "Testing deployment..."

    # Wait for service to be ready
    sleep 5

    # Test health endpoint
    if curl -sf "${SERVICE_URL}/health" > /dev/null; then
        log_info "Health check passed ✅"
    else
        log_warn "Health check failed. Check logs: gcloud run logs read ${SERVICE_NAME} --region=${REGION}"
    fi
}

show_logs() {
    log_info "Showing logs (press Ctrl+C to exit)..."
    gcloud run logs tail "${SERVICE_NAME}" --region="${REGION}"
}

main() {
    log_info "Starting deployment of ${SERVICE_NAME} to GCP Cloud Run..."
    echo

    # Run deployment steps
    check_prerequisites
    enable_apis
    create_secrets
    create_service_account
    build_image
    push_image
    deploy_cloud_run
    get_service_url
    test_deployment

    echo
    log_info "Deployment complete! 🚀"
    echo
    log_info "Service URL: ${SERVICE_URL}"
    log_info "View logs:   gcloud run logs tail ${SERVICE_NAME} --region=${REGION}"
    log_info "Stop bot:    gcloud run services delete ${SERVICE_NAME} --region=${REGION}"
    echo
    log_info "Cost: \$0/mo (under 2M requests/mo free tier) ✅"
    echo

    # Ask to show logs
    echo -n "Show logs now? (y/n): "
    read -r SHOW_LOGS
    if [[ "${SHOW_LOGS}" == "y" ]]; then
        show_logs
    fi
}

main "$@"
