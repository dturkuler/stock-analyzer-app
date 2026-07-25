#!/usr/bin/env bash
# ==============================================================================
# Stock Analyzer Platform — Docker Build, Release & Cleanup Script
# ==============================================================================
# Usage:
#   ./release.sh                              👉 Build image locally & cleanup old images
#   ./release.sh myrepo/stock-analyzer-app    👉 Build & tag custom repository
#   ./release.sh myrepo/stock-analyzer-app --push 👉 Build, tag & push to Docker registry
#   ./release.sh --push                       👉 Build & push default image to registry
# ==============================================================================

set -e

# Default Configuration
IMAGE_NAME="${DOCKER_IMAGE:-stock-analyzer-app}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TAG="${VERSION_TAG:-$TIMESTAMP}"
PUSH=false
NO_CACHE=""

# Parse Arguments
for arg in "$@"; do
    case $arg in
        --push)
            PUSH=true
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            ;;
        -h|--help)
            echo "Usage: ./release.sh [IMAGE_NAME] [--push] [--no-cache]"
            echo ""
            echo "Options:"
            echo "  IMAGE_NAME   Docker image repository (default: stock-analyzer-app)"
            echo "  --push       Push image to registry after building"
            echo "  --no-cache   Build image without using cache"
            exit 0
            ;;
        *)
            if [[ "$arg" != -* ]]; then
                IMAGE_NAME="$arg"
            fi
            ;;
    esac
done

echo "======================================================================"
echo "🚀 Stock Analyzer Platform Docker Release Pipeline"
echo "======================================================================"
echo "📦 Image Repository : ${IMAGE_NAME}"
echo "🏷️  Release Tag      : ${TAG}"
echo "🏷️  Latest Tag       : latest"
echo "⬆️  Push to Registry : ${PUSH}"
echo "======================================================================"

# 1. Capture Old Image Tags for Cleanup
echo ""
echo "🔍 Searching for existing image versions to prune after build..."
OLD_TAGS=$(docker images --format "{{.Repository}}:{{.Tag}}" "${IMAGE_NAME}" 2>/dev/null | grep -v "<none>" || true)
if [ -n "$OLD_TAGS" ]; then
    echo "Found old image tag(s):"
    echo "$OLD_TAGS"
else
    echo "No existing images found for ${IMAGE_NAME}."
fi

# 2. Build Docker Image
echo ""
echo "🔨 Building Docker image: ${IMAGE_NAME}:${TAG} and ${IMAGE_NAME}:latest..."
docker build ${NO_CACHE} \
    -t "${IMAGE_NAME}:${TAG}" \
    -t "${IMAGE_NAME}:latest" \
    .

echo "✅ Docker build completed successfully."

# 3. Restart Running Compose Containers (if applicable)
if [ -f "docker-compose.yml" ]; then
    echo ""
    echo "🔄 Switching running Docker containers to newly built image..."
    docker compose up -d
fi

# 4. Push to Registry (Optional)
if [ "$PUSH" = true ]; then
    echo ""
    echo "⬆️ Pushing ${IMAGE_NAME}:${TAG} to Docker registry..."
    docker push "${IMAGE_NAME}:${TAG}"
    
    echo "⬆️ Pushing ${IMAGE_NAME}:latest to Docker registry..."
    docker push "${IMAGE_NAME}:latest"
    echo "✅ Image pushed to registry successfully."
else
    echo ""
    echo "ℹ️ Push skipped (use '--push' flag to push to Docker registry)."
fi

# 5. Clean Up Old / Dangling Docker Images
echo ""
echo "🧹 Cleaning up old image tags and dangling build artifacts..."
if [ -n "$OLD_TAGS" ]; then
    for old_tag in $OLD_TAGS; do
        if [ "$old_tag" != "${IMAGE_NAME}:${TAG}" ] && [ "$old_tag" != "${IMAGE_NAME}:latest" ]; then
            echo "Removing superseded image tag: $old_tag"
            docker rmi -f "$old_tag" 2>/dev/null || true
        fi
    done
fi

echo "Removing dangling Docker images..."
docker image prune -f

echo ""
echo "======================================================================"
echo "🎉 Release Complete!"
echo "Built Images:"
docker images "${IMAGE_NAME}"
echo "======================================================================"
