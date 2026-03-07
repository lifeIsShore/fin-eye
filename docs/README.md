# Fin-Eye — Documentation Index

> **Educational market intelligence platform** · Not financial advice

---

## 📋 Active Documents

| Document | Description |
|----------|-------------|
| [`PRE-LAUNCH-STRATEGY.md`](./PRE-LAUNCH-STRATEGY.md) | **START HERE** — Security audit, product gaps, advanced indicators roadmap, ML expansion, digital nomad content, tax structures, digital showroom strategy, pre-launch checklist |
| [`architecture.md`](./architecture.md) | System architecture: backend services, data flow, ML pipeline, caching strategy |
| [`api-reference.md`](./api-reference.md) | All API endpoints with request/response schemas |
| [`blueprint.md`](./blueprint.md) | Original product blueprint and technical decisions |
| [`backup-runbook.md`](./backup-runbook.md) | Database backup and disaster recovery procedures |

## 🗂 Root-Level Documents

| Document | Description |
|----------|-------------|
| [`/implementation-log.md`](../implementation-log.md) | Per-story implementation log — what was built, decisions, file list |
| [`/user-stories.md`](../user-stories.md) | All user stories with acceptance criteria |
| [`/prdv3.md`](../prdv3.md) | Full Product Requirements Document v3 |
| [`/brainstormıng-fate.md`](../brainstormıng-fate.md) | Early brainstorming and product direction notes |

## 📦 Archive (superseded documents)

Older documents moved to [`docs/archive/`](./archive/) — kept for historical reference only.

| Document | Notes |
|----------|-------|
| `SPRINT-1-SUMMARY.md` | Sprint 1 summary — superseded by implementation-log |
| `fin-eye-progress-v2.md` | Progress v2 — superseded |
| `fin-eye-stories-v2.md` | Stories v2 — superseded by user-stories.md |
| `IMPLEMENTATION-SUMMARY.md` | High-level summary — superseded by implementation-log |
| `NEXT-STEPS.md` | Old next steps — superseded by PRE-LAUNCH-STRATEGY.md |
| `fin-eye-b2b2c-architecture.md` | B2B2C architecture proposal — archived |

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
cd backend && pip install -r requirements.txt
cd frontend && npm install

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit .env with your API keys

# 3. Seed all data (first time)
cd backend && python scripts/seed_all_data.py --fast

# 4. Start services
# Terminal 1: uvicorn app.main:app --reload
# Terminal 2: cd frontend && npm run dev

# 5. Open
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
# Admin:    admin@fin-eye.com / AdminFinEye2024!
```

## 🔐 Security Status

> ⚠️ **Before any public deployment:** See **Section 1** of `PRE-LAUNCH-STRATEGY.md` for critical security issues that must be addressed, including rotating committed secrets and enabling auth enforcement.

---

*Last updated: 2026-03-07*
