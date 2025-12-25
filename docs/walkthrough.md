# Replication & HA Demo Verification Walkthrough

## Overview
This walkthrough documents the verification of the **Replication & High Availability** feature. The goal is to confirm that the Master-Slave replication is working and that the demo correctly visualizes replication lag.

## Verification Steps

### 1. Infrastructure Setup
We updated `docker-compose.yml` to include a `db_replica` service.

**Action Required:**
You must restart the Docker containers to apply the changes.
```bash
docker-compose down
docker-compose up -d --build
```

### 2. Replication Status Check
Verify that the replica is running and replicating.

**Command:**
```bash
docker-compose logs db_replica
```
**Expected Output:**
You should see logs indicating:
- `entering standby mode`
- `started streaming WAL from primary`
- `consistent recovery state reached`

### 3. Running the Demo
Navigate to the ADBMS Dashboard and select "Replication & HA".

**URL:** `http://localhost:8000/adbms/replication/`

**Expected Results:**
- **Primary Value:** Shows the new capacity set on the Primary.
- **Replica Value:** Shows the value read from the Replica.
- **Sync Status:**
    - If "Synced": Replication was fast enough (common in low-load dev env).
    - If "Lagging": The replica hasn't caught up yet.
- **LSN Values:** Should be identical or very close.

### 4. Troubleshooting
If the replica fails to start:
- Check if `config/db/primary/pg_hba.conf` is correctly mounted and allows replication.
- Check if `config/db/primary/postgresql.conf` has `wal_level = replica`.
- Ensure `db` service is healthy before `db_replica` starts.
