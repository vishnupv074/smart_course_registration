# MVCC & Visibility - Multi-Version Concurrency Control in PostgreSQL

## Overview

Multi-Version Concurrency Control (MVCC) is PostgreSQL's fundamental mechanism for handling concurrent access to data. Unlike traditional locking-based systems, MVCC allows multiple transactions to access the same data simultaneously without blocking each other by maintaining multiple versions of each row.

## What is MVCC?

**MVCC (Multi-Version Concurrency Control)** is a concurrency control method that:
- Maintains multiple versions of data rows simultaneously
- Allows readers to access data without blocking writers
- Allows writers to modify data without blocking readers
- Provides each transaction with a consistent snapshot of the database

### Key Benefits

1. **High Concurrency**: Readers never block writers, and writers never block readers
2. **Consistent Snapshots**: Each transaction sees a consistent view of the database
3. **No Read Locks**: SELECT queries don't acquire locks, improving performance
4. **ACID Compliance**: Maintains full transactional guarantees

### Trade-offs

1. **Storage Overhead**: Multiple row versions consume more disk space
2. **VACUUM Requirement**: Dead row versions must be cleaned up periodically
3. **Bloat**: Tables can grow larger than necessary if VACUUM doesn't keep up
4. **Complexity**: Understanding visibility rules requires knowledge of transaction IDs

## How PostgreSQL Implements MVCC

PostgreSQL uses **row versioning** with special system columns to track which transaction created or modified each row version.

### System Columns

Every PostgreSQL table has hidden system columns that track row versioning:

#### 1. **xmin** (Transaction ID - Creator)
- The transaction ID (XID) that **created** this row version
- Set when a row is inserted or updated
- Used to determine if a row version is visible to a transaction

**Example:**
```sql
INSERT INTO courses_section (course_id, capacity, ...) VALUES (...);
-- This creates a new row with xmin = current transaction ID
```

#### 2. **xmax** (Transaction ID - Deleter/Updater)
- The transaction ID that **deleted or updated** this row version
- Set to `0` if the row is still current (not deleted/updated)
- When a row is updated, the old version gets xmax set, and a new version is created

**Example:**
```sql
UPDATE courses_section SET capacity = 100 WHERE id = 1;
-- Old row version: xmax = current transaction ID
-- New row version: xmin = current transaction ID, xmax = 0
```

#### 3. **ctid** (Physical Location)
- The physical location of the row version in the table
- Format: `(page_number, tuple_index)`
- Changes when a row is updated (new version gets new ctid)
- Useful for debugging and understanding physical storage

**Example:**
```
ctid = (0, 1)  -- First tuple on page 0
ctid = (0, 2)  -- Second tuple on page 0
ctid = (1, 1)  -- First tuple on page 1
```

### Viewing System Columns

You can query system columns explicitly:

```sql
SELECT id, capacity, xmin, xmax, ctid 
FROM courses_section 
WHERE id = 1;
```

**Sample Output:**
```
 id | capacity | xmin  | xmax | ctid  
----+----------+-------+------+-------
  1 |       50 | 12345 |    0 | (0,1)
```

## Transaction Snapshots

When a transaction starts, PostgreSQL creates a **snapshot** that determines which row versions are visible to that transaction.

### Snapshot Components

1. **xmin**: Minimum transaction ID still active when snapshot was taken
2. **xmax**: First transaction ID not yet assigned when snapshot was taken
3. **xip_list**: List of transaction IDs that were active when snapshot was taken

### Visibility Rules

A row version is visible to a transaction if:

1. **Row was created by a committed transaction** that started before the current transaction's snapshot
2. **Row has not been deleted** by a transaction that committed before the snapshot
3. **Row was not created by the current transaction** (unless it's the same transaction)

**Simplified Rule:**
- If `row.xmin < snapshot.xmax` AND `row.xmin` is committed AND `row.xmax == 0` OR `row.xmax > snapshot.xmin`
- Then the row is visible

## Demonstration Walkthrough

Our MVCC demo simulates two concurrent transactions to show row versioning in action.

### Initial State

```
Section ID: 1
Capacity: 50
xmin: 12345 (transaction that created/last updated this row)
xmax: 0 (row is current, not deleted)
ctid: (0, 1) (physical location)
```

### Step-by-Step Execution

#### Step 1: Transaction A Starts and Reads
```sql
BEGIN;  -- Transaction A starts (snapshot created)
SELECT id, capacity, xmin, xmax, ctid FROM courses_section WHERE id = 1;
-- Result: capacity=50, xmin=12345, xmax=0, ctid=(0,1)
```

**Transaction A's Snapshot**: Captures the current state of the database

#### Step 2: Transaction B Updates (Background)
```sql
BEGIN;  -- Transaction B starts
UPDATE courses_section SET capacity = 100 WHERE id = 1;
COMMIT; -- Transaction B commits
```

**What Happens Internally:**
1. Old row version: `xmax` is set to Transaction B's ID (e.g., 12350)
2. New row version: Created with `xmin=12350`, `xmax=0`, `ctid=(0,2)`
3. Both versions exist in the table simultaneously

**Row Versions After Transaction B:**
```
Old Version: capacity=50, xmin=12345, xmax=12350, ctid=(0,1)
New Version: capacity=100, xmin=12350, xmax=0, ctid=(0,2)
```

#### Step 3: Transaction A Reads Again (Snapshot Isolation)
```sql
-- Still inside Transaction A
SELECT id, capacity, xmin, xmax, ctid FROM courses_section WHERE id = 1;
-- Result: capacity=50, xmin=12345, xmax=0, ctid=(0,1)
```

**Key Observation**: Transaction A **still sees capacity=50**!

**Why?**
- Transaction A's snapshot was taken before Transaction B committed
- According to visibility rules, the new version (xmin=12350) is not visible to Transaction A
- Transaction A sees the old version that was current when it started

#### Step 4: Transaction A Commits
```sql
COMMIT; -- Transaction A ends, snapshot is released
```

#### Step 5: New Transaction Reads
```sql
BEGIN;  -- New transaction starts (new snapshot)
SELECT id, capacity, xmin, xmax, ctid FROM courses_section WHERE id = 1;
-- Result: capacity=100, xmin=12350, xmax=0, ctid=(0,2)
```

**Now the new version is visible** because the new transaction's snapshot includes Transaction B's commit.

### Visual Timeline

```
T1: Transaction A starts, reads capacity=50 (xmin=12345)
T2: Transaction B starts
T3: Transaction B updates to capacity=100, commits (creates xmin=12350)
T4: Transaction A reads again, STILL sees capacity=50 (snapshot isolation!)
T5: Transaction A commits
T6: New transaction reads, sees capacity=100 (new version visible)
```

## Isolation Levels and MVCC

PostgreSQL's isolation levels are built on top of MVCC:

### READ COMMITTED (Default)
- New snapshot taken for **each statement** within a transaction
- Sees changes committed by other transactions between statements
- **Non-repeatable reads** are possible

### REPEATABLE READ
- Snapshot taken **once at transaction start**
- Sees a consistent view throughout the transaction
- **Phantom reads** are prevented (in PostgreSQL, unlike SQL standard)

### SERIALIZABLE
- Strictest isolation level
- Detects serialization anomalies and aborts conflicting transactions
- Guarantees truly serializable execution

## MVCC vs Traditional Locking

| Aspect | MVCC | Traditional Locking |
|--------|------|---------------------|
| **Read Blocking** | Readers never block | Readers may block writers |
| **Write Blocking** | Writers never block readers | Writers block readers |
| **Concurrency** | Very high | Lower |
| **Storage** | Multiple versions (more space) | Single version |
| **Cleanup** | Requires VACUUM | No cleanup needed |
| **Complexity** | Higher (visibility rules) | Lower |

## Practical Implications

### When MVCC Shines

1. **Read-Heavy Workloads**: Readers don't block, so SELECT queries are fast
2. **Long-Running Reports**: Reports see consistent data without locking
3. **High Concurrency**: Many users can access data simultaneously

### When to Be Careful

1. **Write-Heavy Workloads**: Many updates create many row versions
2. **Long Transactions**: Hold snapshots for extended periods, preventing VACUUM
3. **Bloat**: Tables can grow large if VACUUM doesn't keep up

### Best Practices

1. **Monitor VACUUM**: Ensure autovacuum is running and tuned properly
2. **Avoid Long Transactions**: Keep transactions short to allow cleanup
3. **Use Appropriate Isolation Levels**: Don't use SERIALIZABLE unless necessary
4. **Monitor Bloat**: Check table and index bloat regularly

## VACUUM and Cleanup

MVCC creates dead row versions that must be cleaned up:

### What VACUUM Does

1. **Marks Dead Tuples**: Identifies row versions no longer visible to any transaction
2. **Reclaims Space**: Makes space available for new row versions
3. **Updates Statistics**: Helps query planner make better decisions
4. **Prevents Transaction ID Wraparound**: Critical for database health

### Types of VACUUM

```sql
-- Standard VACUUM (non-blocking)
VACUUM courses_section;

-- VACUUM FULL (locks table, reclaims all space)
VACUUM FULL courses_section;

-- ANALYZE (updates statistics)
ANALYZE courses_section;

-- Combined
VACUUM ANALYZE courses_section;
```

### Autovacuum

PostgreSQL runs autovacuum automatically based on thresholds:

```sql
-- Check autovacuum settings
SHOW autovacuum;
SHOW autovacuum_naptime;
SHOW autovacuum_vacuum_threshold;
```

## Monitoring MVCC Health

### Check Dead Tuples

```sql
SELECT 
    schemaname, 
    relname, 
    n_live_tup, 
    n_dead_tup,
    round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

### Check Table Bloat

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check Long-Running Transactions

```sql
SELECT 
    pid,
    usename,
    state,
    age(clock_timestamp(), xact_start) AS xact_age,
    query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY xact_start;
```

## Comparison with Other DBMS

### MySQL (InnoDB)
- Also uses MVCC with undo logs
- Similar snapshot isolation
- Different implementation (undo logs vs row versions)

### Oracle
- Uses MVCC with undo tablespaces
- Read consistency through undo data
- Similar concepts, different implementation

### SQL Server
- Uses row versioning (optional)
- Snapshot isolation available but not default
- Traditionally more lock-based

## Conclusion

MVCC is a powerful concurrency control mechanism that enables PostgreSQL to handle high-concurrency workloads efficiently. By maintaining multiple row versions and using transaction snapshots, PostgreSQL provides:

- **High concurrency** without read locks
- **Consistent snapshots** for each transaction
- **ACID compliance** with excellent performance

Understanding MVCC, system columns (xmin, xmax, ctid), and visibility rules is essential for:
- Optimizing database performance
- Debugging concurrency issues
- Tuning VACUUM and autovacuum
- Choosing appropriate isolation levels

The trade-off is increased storage overhead and the need for regular VACUUM maintenance, but for most applications, the benefits far outweigh the costs.

## Further Reading

- [PostgreSQL MVCC Documentation](https://www.postgresql.org/docs/current/mvcc.html)
- [PostgreSQL Internals - MVCC](https://www.interdb.jp/pg/pgsql05.html)
- [Understanding VACUUM](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [Transaction Isolation Levels](https://www.postgresql.org/docs/current/transaction-iso.html)
