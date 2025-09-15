#!/bin/bash

# Script: deploy-online-boutique-k8s.sh
# Description: Builds and deploys online-boutique application to Kubernetes with monitoring
# Author: uView Project

# Set strict mode for better error handling
set -euo pipefail

# Usage function
show_usage() {
    cat << EOF
Usage: $0 <APP_NAME> [OPTIONS]

DESCRIPTION:
    This script builds and deploys the online-boutique microservices application
    to Kubernetes with integrated monitoring capabilities, or tears down existing deployments.

ARGUMENTS:
    APP_NAME        Name of the application to deploy (required, should be 'online-boutique')

OPTIONS:
    --force-make     Force rebuild of Helm templates (deploy only)
    --no-run        Skip deploying the application after building (deploy only)
    --down          Tear down the application instead of deploying
    --help, -h      Show this help message

EXAMPLES:
    $0 online-boutique                    # Deploy the application
    $0 online-boutique --force-make       # Deploy with forced template rebuild
    $0 online-boutique --down             # Tear down the application
    $0 online-boutique --no-run           # Build templates but don't deploy

EOF
}

# Function to log messages with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Function to log errors
error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

# Function to validate arguments
validate_arguments() {
    if [[ $# -lt 1 ]]; then
        error "Insufficient arguments provided"
        show_usage
        exit 1
    fi

    local app="$1"

    if [[ -z "$app" ]]; then
        error "APP_NAME cannot be empty"
        show_usage
        exit 1
    fi

    # Validate app directory exists
    if [[ ! -d "$APP_DIR/$app" ]]; then
        error "Application directory '$APP_DIR/$app' not found"
        exit 2
    fi

    # For deploy operations, validate Helm chart exists
    if [[ "$TEAR_DOWN" != true ]]; then
        # Validate Helm chart exists
        if [[ ! -d "$APP_DIR/$app/helm" ]]; then
            error "Helm chart directory '$APP_DIR/$app/helm' not found"
            exit 2
        fi

        # Validate values.yaml exists
        if [[ ! -f "$APP_DIR/$app/helm/values.yaml" ]]; then
            error "Helm values file '$APP_DIR/$app/helm/values.yaml' not found"
            exit 2
        fi
    fi
}

# Function to wait for pods to be ready
wait_for_pods_ready() {
    local timeout="${1:-300}"
    
    log "Waiting for all pods to be ready..."
    
    NAMESPACES=("online-boutique" "observe")

    for namespace in "${NAMESPACES[@]}"; do
        if kubectl get namespace "$namespace" >/dev/null 2>&1; then 
            log "Waiting for pods in namespace '$namespace' to be ready..."
            
            if ! kubectl wait pod \
                --all \
                --for=condition=Ready \
                --namespace="$namespace" \
                --timeout="${timeout}s" 2>/dev/null; then
                error "Timeout waiting for pods to be ready in namespace '$namespace'"
                log "Current pod status:"
                kubectl get pods -n "$namespace"
                return 1
            fi
            
            log "✅ All pods in namespace '$namespace' are ready and running"
        else
            log "Namespace '$namespace' does not exist, skipping..."
        fi
    done
}

# Wait for pods to be terminated in the two hardcoded namespaces
wait_for_pods_terminated() {
    local timeout="${1:-120}"
    
    NAMESPACES=("online-boutique" "observe")

    for namespace in "${NAMESPACES[@]}"; do
        if kubectl get namespace "$namespace" >/dev/null 2>&1; then 
            log "Waiting for pods in namespace '$namespace' to be terminated..."
            
            while true; do
                local pod_count=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null | wc -l)
                
                if [[ $pod_count -eq 0 ]]; then
                    log "✅ All pods in namespace '$namespace' have been terminated"
                    break
                fi
                
                log "Waiting for $pod_count pods to terminate..."
                sleep 5
            done
        else
            log "Namespace '$namespace' does not exist, skipping..."
        fi
    done
}

# Function to check if deployment exists
deployment_exists() {
    local app_dir="$1"
    [[ -f "$app_dir/release/deploy.yaml" ]]
}

# Function to tear down the application
tear_down() {
    local app_path="$1"
    local release_dir="$app_path/release"
    
    log "🔥 Starting application tear down process..."
    
    # Check if deployment manifest exists
    if [[ ! -f "$release_dir/deploy.yaml" ]]; then
        error "Deployment manifest not found: $release_dir/deploy.yaml"
        log "Application may not be deployed or manifest was removed"
        exit 2
    fi
    
    log "Tearing down application from Kubernetes..."
    
    if ! kubectl delete -f "$release_dir/deploy.yaml"; then
        error "Failed to tear down application from Kubernetes"
        exit 3
    fi
    
    log "✅ Tear down command executed successfully"
    
    # Wait for application pods to be terminated
    log "⏳ Waiting for application pods to be terminated..."
    if ! wait_for_pods_terminated 120; then
        error "Some application pods failed to terminate within 2 minutes"
        exit 3
    fi
    
    log "🎉 Application tear down completed successfully!"
    
    # Display summary
    echo ""
    log "=== TEAR DOWN SUMMARY ==="
    log "Application: $APP"
    log "Deployment Manifest: $release_dir/deploy.yaml"
    log "Application pods: Terminated"
    echo ""
    log "Use 'kubectl get pods' to verify no application pods remain"
    
    # Show current pod status
    echo ""
    log "Current pod status:"
    kubectl get pods -n online-boutique 2>/dev/null || log "No pods in online-boutique namespace"
    kubectl get pods -n observe 2>/dev/null || log "No pods in observe namespace"
}

# Check for help flag
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]] || [[ $# -eq 0 ]]; then
    show_usage
    exit 0
fi

# Parse command line arguments
FORCE_MAKE=false
NO_RUN=false
TEAR_DOWN=false

# Process options
for arg in "$@"; do
    case $arg in
        --force-make)
            FORCE_MAKE=true
            ;;
        --no-run)
            NO_RUN=true
            ;;
        --down)
            TEAR_DOWN=true
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
    esac
done

APP="$1"
# SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Load environment variables from .env file if it exists 
# (this is assumed to be done by the caller (e.g., a python script, another script, the user, the editor, etc.))
# if [[ -f "$SCRIPT_DIR/.env" ]]; then
#     log "Loading environment variables from .env file..."
#     set -a
#     source "$SCRIPT_DIR/.env"
#     set +a
# else
#     error ".env file not found in $SCRIPT_DIR directory"
#     exit 2
# fi

# Validate APP_DIR is set
if [[ -z "${APP_DIR:-}" ]]; then
    error "APP_DIR environment variable is not set"
    exit 2
fi

APP_DIR=$(eval echo "$APP_DIR")

log "Username: $USER"
log "Using APP_DIR: $APP_DIR"

# Validate arguments and environment
log "Validating arguments and environment..."
validate_arguments "$@"

# Set application directory
APP_PATH="$APP_DIR/$APP"
HELM_DIR="$APP_PATH/helm"
RELEASE_DIR="$APP_PATH/release"

# Continue with normal deployment process
log "Using APP: $APP"
log "Using FORCE_MAKE: $FORCE_MAKE"
log "Using TEAR_DOWN: $TEAR_DOWN"

# Handle tear down option
if [[ "$TEAR_DOWN" == true ]]; then
    tear_down "$APP_PATH"
    exit 0
fi

log "Starting Kubernetes deployment process..."

# Create release directory if it doesn't exist
if [[ ! -d "$RELEASE_DIR" ]]; then
    log "Creating release directory..."
    mkdir -p "$RELEASE_DIR"
fi

# Step 1: Generate Helm templates
cd "$HELM_DIR"

if [[ "$FORCE_MAKE" == true ]] || ! deployment_exists "$APP_PATH"; then
    log "Generating Helm templates for $APP..."
    
    if ! helm template online-boutique . -f values.yaml > ../release/deploy.yaml; then
        error "Failed to generate Helm templates"
        exit 3
    fi
    
    log "✅ Helm templates generated successfully"
else
    log "💿 Deployment manifest exists, skipping Helm template generation"
fi

if [[ "$NO_RUN" == true ]]; then
    log "🛑 Skipping deployment (--no-run option specified)"
    log "To deploy the app, execute the script without --no-run option"
    exit 0
fi

# Step 2: Deploy to Kubernetes
log "🚀 Deploying application to Kubernetes..."

if ! kubectl apply -f "$RELEASE_DIR/deploy.yaml"; then
    error "Failed to deploy application to Kubernetes"
    exit 3
fi

log "✅ Application deployed successfully"

# Step 3: Wait for application pods to be ready
log "⏳ Waiting for application pods to be ready..."
if ! wait_for_pods_ready 300; then
    error "Pods failed to become ready"
    exit 3
fi

log "🎉 Deployment completed successfully!"

# Display useful information
echo ""
log "=== DEPLOYMENT SUMMARY ==="
log "Application: $APP"
log "Helm Chart: $HELM_DIR"
log "Deployment Manifest: $RELEASE_DIR/deploy.yaml"
log "Application pods: Ready"
if kubectl get namespace observe >/dev/null 2>&1; then
    log "Monitoring pods: Ready"
fi
echo ""
log "Use 'kubectl get pods' to check application pod status"
log "Use 'kubectl get pods -n observe' to check monitoring pod status"
log "Use 'kubectl logs -f deployment/<service-name>' to follow service logs"
log "Use '$0 $APP --down' to tear down the application"

# Show current pod status
echo ""
log "Current application pod status:"
kubectl get pods

if kubectl get namespace observe >/dev/null 2>&1; then
    echo ""
    log "Current monitoring pod status:"
    kubectl get pods -n observe
fi