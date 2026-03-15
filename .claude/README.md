# Fin-Eye Claude Skills & Agents System

This folder contains two things:
- **Skills** — markdown files Claude reads to understand fin-eye's domain, conventions, and standards
- **Agents** — runnable Python scripts that use local Ollama LLMs to evaluate, validate, and gate ML outputs

Both are self-contained. You can zip this entire `.claude/` folder and send it to a colleague and it will work on their machine (with or without Ollama — agents degrade gracefully).

---

## Folder Structure

```
.claude/
├── README.md                          ← you are here
├── skills/
│   ├── backend-fastapi.md             ← FastAPI/SQLAlchemy patterns for fin-eye
│   ├── frontend-nextjs-fintech.md     ← Next.js + financial dashboard conventions
│   ├── ml-signal-evaluation.md        ← how to judge ML signal quality
│   ├── external-data-reasonability.md ← data feed sanity standards
│   ├── ml-cicd-retraining.md          ← when and how to retrain models
│   ├── fintech-signal-interpretation.md ← finance domain knowledge for devs
│   ├── senior-ux-fintech.md           ← UX patterns for financial dashboards
│   └── fintech-product-manager.md     ← product prioritization frameworks
└── agents/
    ├── README.md                      ← HOW & WHEN TO RUN AGENTS (start here)
    ├── config.yaml                    ← Ollama model routing + thresholds config
    ├── ml_output_evaluator.py         ← evaluates trained model quality
    ├── data_quality_checker.py        ← validates OHLCV + macro data feeds
    ├── gas_sanity_agent.py            ← checks GAS snapshot reasonability
    └── cicd_model_gate.py             ← challenger vs champion promotion gate
```

---

## Quick Start

```bash
# Install agent dependencies (one time)
pip install requests pyyaml

# Check if Ollama is running
curl http://localhost:11434/api/tags

# Run the most important agent after any ML training run
cd fin-eye/.claude/agents
python ml_output_evaluator.py --symbol AAPL --timeframe 1h
```

See `agents/README.md` for full trigger rules and CI/CD integration guide.

---

## How Skills Are Used

When working in fin-eye with Claude, reference a skill by saying:
> "Read `.claude/skills/ml-signal-evaluation.md` before reviewing this training run."

Skills are plain markdown — no tooling required. Drop relevant skill content into the conversation context when you want Claude to apply domain-specific standards.

---

## Colleague Setup

If you received this folder from a colleague:

1. Copy `.claude/` into the root of the fin-eye project.
2. Run `pip install requests pyyaml` for agent dependencies.
3. **If you have Ollama:** ensure `ollama serve` is running and models are pulled (see `agents/config.yaml`).
4. **If you don't have Ollama:** agents still run — they skip LLM calls and produce a structured checklist report. All numeric thresholds and rule-based logic still apply.

Required Ollama models (only needed for LLM-enhanced evaluation):
```bash
ollama pull deepseek-r1:32b
ollama pull gemma2:27b
ollama pull qwen2.5-coder:32b
```
