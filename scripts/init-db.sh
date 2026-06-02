#!/bin/bash
# Create Cognee's database alongside CortexBrain's database
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE cognee_db OWNER cortexbrain;
EOSQL
