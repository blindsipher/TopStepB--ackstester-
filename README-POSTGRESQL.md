# PostgreSQL Setup for TopStepB
Author: blindsipher

This document explains how to set up PostgreSQL for the optimization storage used by TopStepB. The optimization engine uses PostgreSQL for distributed studies and falls back to local SQLite if PostgreSQL is not reachable.

Scope
- Applies to the project in `TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY`
- No emojis or special symbols are used in this document

## Why PostgreSQL
- Enables multi-process and multi-machine optimization using Optuna RDBStorage
- Provides durability for studies, trials, metrics, and checkpoints
- Allows resuming, monitoring, and scaling optimization jobs

## Where To Configure In The Code
Edit the storage settings in:
- `TopStepB - MAIN CLEAN - BEFORE SECOND STRATEGY/optimization/config/optuna_config.py: StorageConfig`

Fields to update in `StorageConfig`:
- `host` (e.g., `localhost` or a server address)
- `port` (default in this repo may be `1127`; the common default is `5432`)
- `database` (e.g., `optuna_optimization`)
- `username` (e.g., `postgres`)
- `password` (your password)

Connection string format used by the engine:
```
postgresql://<username>:<password>@<host>:<port>/<database>
```

If PostgreSQL connection fails, the engine automatically falls back to SQLite in the run results directory.

## Installation

Windows
1) Download and install PostgreSQL from https://www.postgresql.org/download/windows/
2) During setup, note the superuser name (usually `postgres`), password, and port
3) Ensure the PostgreSQL service is running

Ubuntu/Debian
```
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

RHEL/CentOS/Fedora
```
sudo dnf install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

## Create Database and User

Interactive psql session (local machine):
```
psql -U postgres -h localhost -p 5432
```

Inside psql:
```
-- Create a database for Optuna studies
CREATE DATABASE optuna_optimization;

-- Create a dedicated user and set a password
CREATE USER optuna_user WITH PASSWORD 'your_password_here';

-- Grant privileges to the user on the database
GRANT ALL PRIVILEGES ON DATABASE optuna_optimization TO optuna_user;
```

Update `StorageConfig` to match:
```
host = "localhost"
port = 5432
database = "optuna_optimization"
username = "optuna_user"
password = "your_password_here"
```

## Network Access (Optional, for remote workers)
If workers connect from another machine:
1) In `postgresql.conf`, set `listen_addresses = '*'` or the specific interface
2) In `pg_hba.conf`, allow client IPs, for example:
```
host    all    all    192.168.1.0/24    md5
```
3) Restart PostgreSQL and open the TCP port in your firewall

Windows PowerShell (open port 5432 example):
```
New-NetFirewallRule -DisplayName "PostgreSQL 5432" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow
```

Linux UFW example:
```
sudo ufw allow 5432/tcp
```

## Test The Connection

Using psql:
```
psql "postgresql://optuna_user:your_password_here@localhost:5432/optuna_optimization"
```

If the connection succeeds, the optimization engine will be able to create and run studies.

## Pooling and Concurrency Notes
- The engine configures SQLAlchemy connection pooling for high concurrency
- If you run many workers, ensure PostgreSQL `max_connections` is high enough
- Monitor server resource usage and tune pool sizes as needed

## Troubleshooting
- Connection refused: PostgreSQL not running, wrong port, or firewall blocking
- FATAL: password authentication failed: wrong `username` or `password`
- FATAL: database does not exist: create the database or correct the name
- Timeout: verify network path and server load

## Summary
1) Install PostgreSQL
2) Create database and user
3) Update `StorageConfig` in `optimization/config/optuna_config.py`
4) Test connectivity with psql
5) Run the optimization normally; if PostgreSQL is unavailable, SQLite fallback is automatic

