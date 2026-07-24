#!/usr/bin/env bash
# Pre-commit hook: block secrets from being committed
# Called by .pre-commit-config.yaml (env-leak-check hook)
set -euo pipefail

staged=$(git diff --cached --name-only)

if echo "$staged" | grep -qE '^\.env$|\.env\.|\.pem$|\.key$'; then
  echo "ERROR: secret file detected in staged files"
  echo "  Add it to .gitignore and unstage it:"
  echo "    git reset HEAD <file>"
  exit 1
fi

# Check staged file contents for common secret patterns
for file in $staged; do
  if [ ! -f "$file" ]; then
    continue
  fi
  if git diff --cached -- "$file" | grep -qE '^\+.*(SUDO_PWD|password|secret|api_key|AWS_SECRET|PRIVATE_KEY)'; then
    echo "ERROR: potential secret in $file"
    echo "  Matched pattern in added lines. Review and remove."
    exit 1
  fi
done

exit 0
