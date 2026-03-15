#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# fin-eye pre-push git hook
#
# Automatically runs the ML quality gate when ML-related files are changed.
# Blocks the push if the trained model does not meet quality standards.
#
# SETUP (run once):
#   cp fin-eye/.claude/agents/pre-push.sh fin-eye/.git/hooks/pre-push
#   chmod +x fin-eye/.git/hooks/pre-push
#
# To bypass in emergencies (use sparingly):
#   git push --no-verify
# ─────────────────────────────────────────────────────────────────────────────

set -e

AGENTS_DIR="$(git rev-parse --show-toplevel)/.claude/agents"
CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only --cached)

echo ""
echo "🔍 fin-eye pre-push hook running..."

# ── Check if any ML-critical files changed ────────────────────────────────────
ML_CHANGED=false
if echo "$CHANGED" | grep -qE "ml_pipeline|feature_builder|technical_service|technical_training"; then
  ML_CHANGED=true
fi

if [ "$ML_CHANGED" = false ]; then
  echo "✅ No ML files changed — skipping ML quality gate."
  echo ""
  exit 0
fi

echo "⚡ ML files changed — running quality gate..."
echo "   Changed files:"
echo "$CHANGED" | grep -E "ml_pipeline|feature_builder|technical_service|technical_training" | sed 's/^/   - /'
echo ""

# ── Check Python is available ─────────────────────────────────────────────────
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
  echo "⚠️  Python not found — skipping ML gate (install Python to enable)."
  exit 0
fi

PYTHON=$(command -v python3 || command -v python)

# ── Check agent dependencies ──────────────────────────────────────────────────
if ! $PYTHON -c "import requests, yaml" 2>/dev/null; then
  echo "⚠️  Agent dependencies not installed. Run: pip install requests pyyaml"
  echo "   Skipping ML gate."
  exit 0
fi

# ── Run the evaluator on the last trained model ───────────────────────────────
echo "Running ml_output_evaluator (ci-mode: no Ollama required)..."
echo ""

$PYTHON "$AGENTS_DIR/ml_output_evaluator.py" --from-registry --last-trained --ci-mode

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo ""
  echo "❌ PUSH BLOCKED: ML quality gate failed."
  echo "   Fix the model quality issues shown above before pushing."
  echo "   To bypass (emergency only): git push --no-verify"
  echo ""
  exit 1
fi

echo ""
echo "✅ ML quality gate passed. Proceeding with push."
echo ""
exit 0
