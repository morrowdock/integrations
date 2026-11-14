#!/usr/bin/env bash
set -euo pipefail
# Pinned release and checksum from its published checksums.txt (2026-11-14).
scan_root=$(git rev-parse --show-toplevel)
scan_dir=$(mktemp -d)
trap 'rm -rf "$scan_dir"' EXIT
curl --fail --silent --show-error --location \
  https://github.com/gitleaks/gitleaks/releases/download/v8.24.3/gitleaks_8.24.3_linux_x64.tar.gz \
  --output "$scan_dir/gitleaks.tar.gz"
printf '%s  %s\n' 9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c "$scan_dir/gitleaks.tar.gz" | sha256sum --check --status
tar -xzf "$scan_dir/gitleaks.tar.gz" -C "$scan_dir" gitleaks
"$scan_dir/gitleaks" git "$scan_root" --redact --no-banner
