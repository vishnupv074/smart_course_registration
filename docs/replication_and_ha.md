# Replication & High Availability (HA)

This document details the implementation of **PostgreSQL Master-Slave Replication** in the Smart Course Registration System.

## 1. Concept Overview

**Replication** is the process of copying data from one database server (Primary) to one or more other servers (Replicas).

### Key Concepts
*   **Primary (Master):** Handles all Write operations (INSERT, UPDATE, DELETE) and Read operations.
*   **Replica (Slave/Standby):** A read-only copy of the database. It receives updates from the Primary via the Write-Ahead Log (WAL).
*   **Asynchronous Replication:** The Primary commits a transaction locally and returns success to the client *before* the Replica has confirmed it received the data.
    *   **Pros:** High performance, low latency for writes.
    *   **Cons:** Potential data loss if Primary fails before sending WAL; **Replication Lag**.
*   **Replication Lag:** The time delay between a commit on the Primary and its visibility on the Replica.

## 2. Implementation Details

We use **Docker Compose** to simulate a Primary-Replica architecture.

### Infrastructure (`docker-compose.yml`)
*   **`db` (Primary):**
    *   Standard PostgreSQL 16 container.
    *   Configured with `wal_level = replica`.
    *   Allows replication connections in `pg_hba.conf`.
*   **`db_replica` (Replica):**
    *   PostgreSQL 16 container.
    *   **Bootstrap:** On first launch, it checks if its data directory is empty. If so, it runs `pg_basebackup` to clone the Primary.
    *   **Standby Mode:** Creates a `standby.signal` file to tell PostgreSQL to start in standby mode.
    *   **Port:** Exposed on `5433` (mapped to internal 5432).

### Configuration
**Primary (`postgresql.conf`):**
```ini
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
```

**Replica (`postgresql.conf` / `postgresql.auto.conf`):**
*   `hot_standby = on` (Default in recent Postgres versions when standby.signal is present).
*   `primary_conninfo`: Connection string to the Primary.

### Django Integration
*   **`settings.py`:** Defines a `replica` database connection pointing to the `db_replica` service.
*   **`adbms_demo/views.py`:** The `replication_demo` view explicitly routes read queries to the replica using `.using('replica')`.

## 3. The Demo

The **Replication & HA Demo** visualizes the concept of **Eventual Consistency**.

### Workflow
1.  **Write:** The application updates the capacity of a specific Section on the **Primary** database.
2.  **Read:** Immediately (within milliseconds), the application reads the same Section from the **Replica** database.
3.  **Compare:** The system compares the two values.
    *   If they match, replication was fast enough (Synced).
    *   If they differ, we observe **Replication Lag**.

### Metrics
*   **Primary LSN (Log Sequence Number):** The current position in the WAL on the Primary.
*   **Replica LSN:** The last WAL position replayed by the Replica.
*   **Lag Bytes:** The difference between the two LSNs, showing exactly how much data the Replica is behind.

## 4. How to Run
1.  Ensure the Docker stack is running: `docker-compose up -d`.
2.  Navigate to the **ADBMS Dashboard**.
3.  Click on the **Replication & HA** card.
4.  Observe the Primary and Replica values.
    *   *Note: In a local environment with low load, replication is often near-instantaneous, so you might see "Synced" most of the time. To force lag, one would need to generate heavy write load.*
