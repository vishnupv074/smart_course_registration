# Partitioning Demo Verification Walkthrough

## Overview
This walkthrough documents the verification of the **Table Partitioning** feature in the Smart Course Registration System. The goal was to confirm that partitioning is correctly implemented and provides performance benefits through **Partition Pruning**.

## Verification Steps

### 1. Database Schema Verification
We verified that the `adbms_demo_partitionedenrollment` table is correctly partitioned by `LIST (semester)`.

**Command:**
```bash
docker-compose exec db psql -U postgres -d course_db -c "\d+ adbms_demo_partitionedenrollment"
```

**Result:**
The table exists and has the following partitions:
- `adbms_demo_partitionedenrollment_fall2024`
- `adbms_demo_partitionedenrollment_spring2025`
- `adbms_demo_partitionedenrollment_fall2025`
- `adbms_demo_partitionedenrollment_spring2026`

### 2. Performance Benchmark
We ran the partitioning demo which compares a query on a standard table vs. a partitioned table.

**URL:** `http://localhost:8000/adbms/partitioning/`

**Results:**

| Metric | Non-Partitioned Table | Partitioned Table |
| :--- | :--- | :--- |
| **Query** | `SELECT * FROM non_partitioned WHERE semester = 'Fall 2024'` | `SELECT * FROM partitioned WHERE semester = 'Fall 2024'` |
| **Execution Time** | **1.784 ms** | **0.750 ms** |
| **Plan Node** | `Seq Scan` on `adbms_demo_nonpartitionedenrollment` | `Seq Scan` on `adbms_demo_partitionedenrollment_fall2024` |
| **Rows Filtered** | 15,051 (Scanned all rows) | 0 (Scanned only relevant partition) |

### Conclusion
The demo successfully demonstrates **Partition Pruning**. The query on the partitioned table was significantly faster (~2.3x) because it only scanned the relevant partition (`fall2024`), whereas the non-partitioned query had to scan the entire table and filter out 75% of the rows.
