# Monitoring & Statistics Demo

## Overview

This demo demonstrates PostgreSQL's **`pg_stat_statements`** extension, which provides detailed query performance monitoring and statistics tracking. The extension captures execution metrics for all SQL statements, enabling database administrators and developers to identify slow queries, analyze performance patterns, and optimize database operations.

## Theory

### What is pg_stat_statements?

`pg_stat_statements` is a PostgreSQL extension that tracks planning and execution statistics for all SQL statements executed by the server. It maintains a shared memory hash table to store statistics about queries, normalized by their structure (removing literal values).

### Key Concepts

#### 1. Query Normalization
The extension normalizes queries by replacing literal values with placeholders. For example:
- `SELECT * FROM users WHERE id = 1`
- `SELECT * FROM users WHERE id = 2`

Both become: `SELECT * FROM users WHERE id = $1`

This allows aggregation of statistics across similar queries with different parameters.

#### 2. Performance Metrics

The extension tracks several critical metrics:

| Metric | Description |
|--------|-------------|
| **calls** | Number of times the query was executed |
| **total_exec_time** | Total time spent executing this query (milliseconds) |
| **mean_exec_time** | Average execution time per call (milliseconds) |
| **min_exec_time** | Minimum execution time observed |
| **max_exec_time** | Maximum execution time observed |
| **stddev_exec_time** | Standard deviation of execution times |
| **rows** | Total number of rows returned/affected |
| **blks_hit** | Number of blocks found in cache (buffer hits) |
| **blks_read** | Number of blocks read from disk |

#### 3. Cache Hit Ratio

The cache hit ratio indicates how often data is found in PostgreSQL's shared buffer cache versus being read from disk:

```
Cache Hit Ratio = (blks_hit / (blks_hit + blks_read)) × 100%
```

A higher ratio (>90%) indicates better performance, as disk I/O is significantly slower than memory access.

## Implementation

### 1. Extension Setup

The demo uses a Django migration to enable the extension:

```python
migrations.RunSQL(
    sql="CREATE EXTENSION IF NOT EXISTS pg_stat_statements;",
    reverse_sql="-- Extension preserved on rollback"
)
```

### 2. View Function

The `monitoring_stats_demo` view performs the following operations:

1. **Extension Check**: Verifies `pg_stat_statements` is enabled
2. **Sample Workload**: Executes sample queries if statistics are sparse
3. **Top Queries**: Retrieves the 15 slowest queries by total execution time
4. **Metrics Calculation**: Computes aggregate statistics
5. **Latency Histogram**: Groups queries by execution time ranges
6. **Cache Analysis**: Calculates buffer cache hit ratio

### 3. Query Examples

#### Retrieving Top Queries
```sql
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    min_exec_time,
    max_exec_time,
    stddev_exec_time,
    rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 15;
```

#### Latency Distribution
```sql
SELECT 
    CASE 
        WHEN mean_exec_time < 0.1 THEN '0-0.1ms'
        WHEN mean_exec_time < 1 THEN '0.1-1ms'
        WHEN mean_exec_time < 10 THEN '1-10ms'
        WHEN mean_exec_time < 100 THEN '10-100ms'
        WHEN mean_exec_time < 1000 THEN '100-1000ms'
        ELSE '1000ms+'
    END as latency_bucket,
    COUNT(*) as query_count
FROM pg_stat_statements
GROUP BY latency_bucket;
```

## Visualization

### Performance Metrics Dashboard

The demo displays four key metrics in card format:

1. **Unique Queries**: Total number of distinct query patterns
2. **Total Executions**: Sum of all query calls
3. **Avg Execution Time**: Mean execution time across all queries
4. **Cache Hit Ratio**: Percentage of data found in memory

### Latency Histogram

A Chart.js bar chart visualizes the distribution of queries across latency ranges:
- **0-0.1ms**: Ultra-fast queries (index lookups)
- **0.1-1ms**: Fast queries (simple selects)
- **1-10ms**: Normal queries (small joins)
- **10-100ms**: Slow queries (complex joins, aggregations)
- **100-1000ms**: Very slow queries (full table scans)
- **1000ms+**: Critical performance issues

### Top Queries Table

An interactive table displays:
- **Query Text**: Truncated SQL with expandable full text
- **Calls**: Execution frequency
- **Total Time**: Cumulative execution time (color-coded badges)
- **Mean Time**: Average per-call execution time
- **Min/Max**: Execution time range
- **Rows**: Total rows processed

Color coding:
- 🟢 **Green (Fast)**: < 1ms total or < 0.5ms mean
- 🟡 **Yellow (Medium)**: 1-10ms total or 0.5-5ms mean
- 🔴 **Red (Slow)**: > 10ms total or > 5ms mean

## Use Cases

### 1. Identifying Slow Queries

Sort queries by `total_exec_time` to find queries consuming the most database time:
```sql
SELECT query, total_exec_time, calls
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

### 2. Finding Frequently Executed Queries

Identify queries that run most often (candidates for caching):
```sql
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 10;
```

### 3. Detecting Performance Regressions

Monitor `mean_exec_time` over time to detect degradation:
- Sudden increases may indicate missing indexes
- Growing standard deviation suggests inconsistent performance

### 4. Optimizing Cache Usage

Low cache hit ratios indicate:
- Insufficient `shared_buffers` configuration
- Queries scanning large tables unnecessarily
- Need for query optimization or indexing

## PostgreSQL Configuration

### Enabling the Extension

1. **Add to postgresql.conf**:
```ini
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
pg_stat_statements.max = 10000
```

2. **Restart PostgreSQL**:
```bash
docker-compose restart db
```

3. **Create Extension** (via migration):
```sql
CREATE EXTENSION pg_stat_statements;
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `pg_stat_statements.max` | 5000 | Maximum number of statements tracked |
| `pg_stat_statements.track` | top | Track top-level, all, or no statements |
| `pg_stat_statements.track_utility` | on | Track utility commands (CREATE, DROP, etc.) |
| `pg_stat_statements.save` | on | Save statistics across server restarts |

## Optimization Strategies

### 1. Index Creation

If a query shows high execution time with many sequential scans:
```sql
CREATE INDEX idx_users_email ON users(email);
```

### 2. Query Rewriting

Replace inefficient patterns:
```sql
-- Inefficient
SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at) = 2024;

-- Efficient
SELECT * FROM orders WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
```

### 3. Connection Pooling

High call counts with short execution times may benefit from connection pooling (PgBouncer).

### 4. Materialized Views

Frequently executed complex queries can be pre-computed:
```sql
CREATE MATERIALIZED VIEW enrollment_summary AS
SELECT course_id, COUNT(*) as student_count
FROM enrollments
GROUP BY course_id;
```

## Monitoring Best Practices

1. **Regular Review**: Check statistics weekly to identify trends
2. **Reset Statistics**: Clear stats after optimization to measure impact
   ```sql
   SELECT pg_stat_statements_reset();
   ```
3. **Set Baselines**: Establish normal performance ranges for critical queries
4. **Alert on Anomalies**: Monitor for sudden spikes in execution time
5. **Correlate with Load**: Compare statistics with system load metrics

## Limitations

1. **Memory Overhead**: Tracking many queries consumes shared memory
2. **Normalization**: Cannot distinguish performance by parameter values
3. **Aggregation**: Individual slow executions may be hidden in averages
4. **No Historical Data**: Only current statistics are maintained

## Related Concepts

- **EXPLAIN ANALYZE**: Detailed execution plans for individual queries
- **pg_stat_activity**: Real-time view of active connections and queries
- **Auto-EXPLAIN**: Automatically log slow query plans
- **Query Optimization**: Using indexes, partitioning, and query rewriting

## References

- [PostgreSQL pg_stat_statements Documentation](https://www.postgresql.org/docs/current/pgstatstatements.html)
- [Query Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- [Monitoring Database Activity](https://www.postgresql.org/docs/current/monitoring-stats.html)
