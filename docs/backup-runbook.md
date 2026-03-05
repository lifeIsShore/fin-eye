# Fin-Eye Backup & Disaster Recovery Runbook (CORE-SEC-02)

## Overview

| What | Detail |
|---|---|
| Backup type | PostgreSQL custom-format dump (`pg_dump -Fc`) |
| Schedule | Daily at **02:00 UTC** (automated via APScheduler) |
| Local retention | 14 days (configurable via `BACKUP_RETAIN_DAYS`) |
| Offsite | S3 (optional, configure `BACKUP_S3_BUCKET`) |
| Script | `backend/scripts/backup/backup_db.py` |
| Restore script | `backend/scripts/backup/restore_db.py` |
| Admin UI | `/admin/ops` → Database Backups panel |

---

## Environment Variables

Set these in your `.env` or deployment environment:

```env
# Required (same as app)
DATABASE_URL=postgresql://user:pass@host:5432/fin_eye

# Backup directory (default: ./backups relative to where script runs)
BACKUP_DIR=/var/backups/fin-eye

# How many days of local files to keep (default: 14)
BACKUP_RETAIN_DAYS=14

# Optional: S3 offsite copy
BACKUP_S3_BUCKET=my-fin-eye-backups
BACKUP_S3_PREFIX=fin-eye-backups/
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=eu-west-1
```

---

## Manual Backup

```bash
cd backend
python scripts/backup/backup_db.py
```

Or trigger from the admin UI: **Ops Dashboard → Database Backups → Backup Now**

Output file: `<BACKUP_DIR>/fin_eye_20260306T020000Z.dump`

---

## Restore Procedure

### Step 1 — Identify the backup file

```bash
ls -lh backups/fin_eye_*.dump
```

Pick the most recent (or specific) file.

### Step 2 — Stop the application (recommended)

Prevents writes during restore. If running via Docker:
```bash
docker-compose stop app
```

### Step 3 — Dry run first (always)

```bash
cd backend
python scripts/backup/restore_db.py \
  --file backups/fin_eye_20260306T020000Z.dump \
  --dry-run
```

This prints the commands without executing them.

### Step 4 — Restore into existing database

Restores objects on top of existing data (`--clean --if-exists`):
```bash
python scripts/backup/restore_db.py \
  --file backups/fin_eye_20260306T020000Z.dump
```

### Step 5 — Full restore (drop and recreate)

**Destructive** — drops all current data first. Use for complete recovery:
```bash
python scripts/backup/restore_db.py \
  --file backups/fin_eye_20260306T020000Z.dump \
  --drop
```

### Step 6 — Restart application

```bash
docker-compose start app
# or
uvicorn app.main:app --reload
```

### Step 7 — Verify

1. Open the app and check the dashboard loads
2. Check `/api/v1/health` returns `"status": "ok"`
3. Check `/admin/ops` — pipeline jobs should show scheduled

---

## Recovery Time Objectives

| Scenario | Expected RTO |
|---|---|
| Single table data loss | < 30 min (restore + verify) |
| Full DB corruption | < 1 hour |
| Host failure (new machine) | 1–2 hours (provision + restore) |

---

## Backup Verification (Monthly)

Run this monthly to confirm backups are restorable:

```bash
# Restore into a test database
createdb fin_eye_test
pg_restore \
  -h localhost -U postgres \
  -d fin_eye_test \
  --no-owner \
  backups/fin_eye_LATEST.dump

# Spot-check
psql -d fin_eye_test -c "SELECT COUNT(*) FROM users;"
psql -d fin_eye_test -c "SELECT COUNT(*) FROM blog_posts;"

# Clean up
dropdb fin_eye_test
```

---

## Monitoring

- Backup job status visible in **Admin → Ops Dashboard → Database Backups**
- Backup failures appear as pipeline errors in **Threshold Alerts**
- If `backup_db` success rate drops below 80%, an alert breach is raised

---

## S3 Offsite Setup (Optional)

1. Create an S3 bucket with versioning enabled
2. Set `BACKUP_S3_BUCKET` in environment
3. Install boto3: `pip install boto3`
4. Backups will upload automatically after each local dump

Recommended bucket policy: enable S3 Intelligent-Tiering to reduce costs on older files.
