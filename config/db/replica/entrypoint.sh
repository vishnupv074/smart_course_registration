#!/bin/bash
set -e

# If data directory is empty, we need to clone from primary
if [ -z "$(ls -A "$PGDATA")" ]; then
    echo "Data directory is empty. Waiting for primary to be ready..."
    
    # Simple wait loop
    until pg_isready -h db -U postgres; do
        echo "Waiting for primary..."
        sleep 2
    done

    echo "Primary is ready. Starting base backup..."
    # PGPASSWORD is required if not using trust auth, but we configured trust in pg_hba.conf
    pg_basebackup -h db -U postgres -D "$PGDATA" -X stream -P -R

    echo "Backup complete. Creating standby signal..."
    # pg_basebackup -R already creates standby.signal and appends to postgresql.auto.conf
    # But let's ensure we are in standby mode
    touch "$PGDATA/standby.signal"
    
    echo "Replica setup complete."
fi

# Execute the original entrypoint
exec docker-entrypoint.sh "$@"
