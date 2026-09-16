#!/bin/bash
set -euo pipefail

PROJECT_DIR="/Users/mithesha/rental-skill"
cd "$PROJECT_DIR"

source .venv/bin/activate
pip install -q -r requirements.txt

export PATH="/Users/mithesha/.local/bin:$PATH"

claude -p "Follow .claude/skills/find-rentals/SKILL.md in this directory exactly, start to finish, including the artifact publish/update step. This is an unattended headless run with no one to show the chat report to, so the published artifact is the actual deliverable -- do not skip it." \
  --add-dir "$PROJECT_DIR" \
  --allowedTools "Bash Read Write Edit Glob Grep Artifact" \
  --permission-mode bypassPermissions \
  --model claude-sonnet-5
