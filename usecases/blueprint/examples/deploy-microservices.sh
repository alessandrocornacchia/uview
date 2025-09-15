#!/bin/bash

# Description: Builds and runs microservices applications with anomaly injection and monitoring

# Set strict mode for better error handling
set -euo pipefail

############################### functions ###############################

##### Usage function
show_usage() {
    cat << EOF
Usage: $0 <APP_NAME> <WIRING_SPEC> [OPTIONS]

DESCRIPTION:
    This script builds and runs microservices applications with integrated
    anomaly injection (FIRM) and monitoring capabilities.

ARGUMENTS:
    APP_NAME        Name of the application to run (required)
    WIRING_SPEC     Wiring specification to use (required)
                    Options: 'original', 'type1failure', or custom spec name. See blueprint/examples/APP_NAME/wiring/specs for available specs.

OPTIONS:
    --force-make-specs    Force rebuild of wiring specifications
    --no-run             Skip running the application after building
    --down               Tear down the application instead of deploying
    --help, -h           Show this help message

EXAMPLES:
    $0 myapp original
    $0 myapp type1failure --force-make-specs
    $0 myapp original --no-run
    $0 myapp original --down
    $0 myapp custom-spec --force-make-specs --no-run

EOF
}

###### Function to log messages with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

###### Function to log errors
error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

###### Function to validate arguments
validate_arguments() {
    if [[ $# -lt 2 ]]; then
        error "Insufficient arguments provided"
        show_usage
        exit 1
    fi

    local app="$1"
    local wiring_spec="$2"

    if [[ -z "$app" ]]; then
        error "APP_NAME cannot be empty"
        show_usage
        exit 1
    fi

    if [[ -z "$wiring_spec" ]]; then
        error "WIRING_SPEC cannot be empty"
        show_usage
        exit 1
    fi

    # Validate app directory exists
    if [[ ! -d "$APPS_DIR/$app" ]]; then
        error "Application directory '$APPS_DIR/$app' not found"
        exit 2
    fi

    # Validate required environment paths
    if [[ ! -d "$FIRM_PATH" ]]; then
        error "FIRM path '$FIRM_PATH' not found"
        exit 2
    fi

    if [[ ! -d "$OBSERVABILITY_PATH" ]]; then
        error "Observability path '$OBSERVABILITY_PATH' not found"
        exit 2
    fi
}


###### Function to tear down the application
tear_down() {
    local docker_dir="$1"
    
    log "🔥 Starting application tear down process..."
    
    # Check if docker directory exists
    if [[ ! -d "$docker_dir" ]]; then
        error "Docker directory not found: $docker_dir"
        log "Application may not be deployed"
        exit 2
    fi
    
    # Check if docker-compose.yml exists
    if [[ ! -f "$docker_dir/docker-compose.yml" ]] && [[ ! -f "$docker_dir/docker-compose.yaml" ]]; then
        error "Docker compose file not found in $docker_dir"
        exit 2
    fi
    
    # Tear down application containers
    log "Tearing down application containers..."
    cd "$docker_dir"
    
    # Load environment variables
    if [[ -f ".env" ]]; then
        set -a
        . .env
        set +a
    fi
    
    # Check for resource settings file
    COMPOSE_FILES=""
    if [[ -f "docker-compose.yaml" ]]; then
        COMPOSE_FILES="-f docker-compose.yaml"
    fi
    if [[ -f "docker-compose.yml" ]]; then
        COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.yml"
    fi
    if [[ -f "deploy-resources.yml" ]]; then
        COMPOSE_FILES="$COMPOSE_FILES -f deploy-resources.yml"
    fi
    
    
    # Stop and remove application containers (accept both yaml and yml extensions)
    COMPOSE_DOWN_CMD="docker compose $COMPOSE_FILES down --remove-orphans"
    log "Executing: $COMPOSE_DOWN_CMD"
    
    if ! eval $COMPOSE_DOWN_CMD; then
        error "Failed to tear down application containers"
        exit 3
    fi
    
    log "🎉 Application tear down completed successfully!"
    
    # Display summary
    echo ""
    log "=== TEAR DOWN SUMMARY ==="
    log "Path: $docker_dir"
    echo ""
    log "Use 'docker compose ps' to verify no containers remain"
    
    # Show current container status
    echo ""
    log "Current container status:"
    docker compose ps -a 2>/dev/null || log "No containers found"
}
############################### functions ###############################



# Main script execution starts here

# Check for help flag
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]] || [[ $# -eq 0 ]]; then
    show_usage
    exit 0
fi

# Parse command line arguments
FORCE_MAKE_SPECS=false
NO_RUN=false
TEAR_DOWN=false

# Process options
for arg in "$@"; do
    case $arg in
        --force-make-specs)
            FORCE_MAKE_SPECS=true
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
APPS_DIR=$(eval echo "$APP_DIR")

# reference to the folder with sample applications
# APPS_DIR="$SCRIPT_DIR/blueprint/examples"

# depending on the app we want to run
BASEDIR=${APPS_DIR}/$APP

# e.g., 'original'
WIRING_SPEC="$2"
BUILD="build/$2"

PROJECT_ROOT=$(eval echo "$PROJECT_ROOT")
FIRM_PATH="$PROJECT_ROOT/usecases/chaos-engineering/anomaly-injector"
OBSERVABILITY_PATH="$PROJECT_ROOT/usecases/observability/docker"

# Validate arguments and environment
log "Validating arguments and environment..."
validate_arguments "$@"

# Handle tear down option EARLY - before any deployment logic
if [[ "$TEAR_DOWN" == true ]]; then
    # app containers
    tear_down "$BASEDIR/build/$WIRING_SPEC/docker"
    # observavility containers
    tear_down "$OBSERVABILITY_PATH"
    exit 0
fi

log "Starting application build and deployment process..."
log "APP: $APP"
log "WIRING_SPEC: $WIRING_SPEC"
log "BASEDIR: $BASEDIR"
log "FORCE_MAKE_SPECS: $FORCE_MAKE_SPECS"
log "NO_RUN: $NO_RUN"



####
# Step-1 : compile FIRM anomaly injector in a container
# Blueprint will copy the compiled binaries from this image into its container images
####


# check if the firm-build image exists, if not build it
log "Checking for firm-build Docker image..."
FIRM_IMAGE=$(docker images firm-build -q)
if [ "$FIRM_IMAGE" == "" ]; then
    log "Building firm-build image..."
    cd $FIRM_PATH
    if ! docker build . -t firm-build; then
        error "Failed to build firm-build image"
        exit 3
    fi
    log "✅ firm-build image built successfully"
else
    log "💿 firm-build image found, skipping build"
fi

## Step 2
# compile the wiring spec for the app
##
log "Preparing wiring specifications..."
cd $BASEDIR

# create the build directory if it does not exist
if [ ! -d "build" ]; then
    log "Creating build directory..."
    mkdir build
fi 

# Check for force rebuild flag
if [[ "$FORCE_MAKE_SPECS" == true ]]; then
    log "Force rebuild requested, cleaning existing build..."
    # add write permissions recursively (this fixes strange behavior for which I get Permission denied
    # while trying to delete these files )
    if [ -d "$BUILD/gotests" ]; then
        chmod -R +w $BUILD/gotests
    fi
    rm -rf $BUILD
fi

# if directory exists we assume the wiring has already been compiled
if [ ! -d "$BUILD" ]; then
    log "Compiling wiring spec for $BUILD..."
    if ! go run $BASEDIR/wiring/main.go -w $WIRING_SPEC -o $BUILD; then
        error "Failed to compile wiring specification"
        exit 3
    fi
    log "✅ Wiring specification compiled successfully"
else
    log "Build found. Skipping compiling wiring spec for $BUILD"
fi

### Step 3
# run the app
###

log "Preparing application environment..."
cd $BUILD

# Validate required files exist
if [ ! -f "./.local.env" ] && [ ! -f "../.local.env" ]; then
    error "Required file '.local.env' not found in $BUILD"
    exit 2
fi

if [ -f "./.local.env" ] ; then
    log "Copying .local.env..."
    cp .local.env ./docker/.env
else
    log "Copying .local.env from parent directory..."
    # here we do not have any more subfolders and we are already in the build directory
    cp ../.local.env .env
fi

# from the build folder we should then go into docker folder
cd ./docker
set -a
. .env
set +a

# copy resource settings (CPU, memory requests and limits), which will be deployed with docker-compose
if [ -f "$BASEDIR/wiring/specs/deploy-resources.yml" ]; then
    log "Copying resource settings..."
    cp $BASEDIR/wiring/specs/deploy-resources.yml ./
    COMPOSE_FILES="-f deploy-resources.yml"
else
    log "No resource settings file found, using defaults"
    COMPOSE_FILES=""
fi



if [[ "$NO_RUN" == true ]]; then
    log "🛑 Skipping running the app (--no-run option specified)"
    log "To run the app, execute the script without --no-run option"
    exit 0
else
    log "🚀 Starting application containers..."
    
    # run the app (merge Blueprint generated compose with resource settings)
    COMPOSE_CMD="docker compose -f docker-compose.yml $COMPOSE_FILES up --build -d"
    log "Executing: $COMPOSE_CMD"
    
    if ! eval $COMPOSE_CMD; then
        error "Failed to start application containers"
        exit 3
    fi
    
    log "✅ Application containers started successfully"

    ### Step 4
    # run the monitoring containers
    ###

    log "🔍 Starting monitoring containers..."
    cd $OBSERVABILITY_PATH
    
    if ! docker compose up -d; then
        error "Failed to start monitoring containers"
        exit 3
    fi
    
    log "✅ Monitoring containers started successfully"
    log "🎉 Deployment completed successfully!"
    
    # Display useful information
    echo ""
    log "=== DEPLOYMENT SUMMARY ==="
    log "Application: $APP"
    log "Wiring Spec: $WIRING_SPEC"
    log "Build Directory: $BUILD"
    log "Application containers: Running"
    log "Monitoring containers: Running"
    echo ""
    log "Use 'docker compose ps' to check container status"
    log "Use 'docker compose logs -f' to follow application logs"
    log "Use '$0 $APP $WIRING_SPEC --down' to tear down the application"
fi


# Handle tear down option
if [[ "$TEAR_DOWN" == true ]]; then
    # app containers
    tear_down "$BASEDIR/build/$WIRING_SPEC/docker"
    # observavility containers
    tear_down "$OBSERVABILITY_PATH"
    exit 0
fi