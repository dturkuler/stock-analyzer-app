#!/usr/bin/env bash
# Auto-generated rollback mechanism for Acquire.com repository reorganization
set -euo pipefail

echo "=== Restoring original repository state ==="

# 1. Restore tracked git state
git reset --hard HEAD 2>/dev/null || true

# 2. Clean generated startup proxies and scripts
rm -f startdev.sh startprd.sh
rm -rf scripts/

echo "✅ Repository restored to pre-Acquire state!"
