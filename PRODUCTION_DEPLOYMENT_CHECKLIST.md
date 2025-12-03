# Production Deployment Checklist
**Status:** ⚠️ 1 CRITICAL FIX REQUIRED
**Review Date:** 2025-12-03
**Overall Score:** 94/100 (Excellent)

---

## CRITICAL: Pre-Deployment Requirements ⚠️

Before deploying to production, you MUST complete these security fixes:

### 🔴 CRITICAL FIX #1: Externalize Database Credentials

**Current Issue:**
```python
# TopStepB/optimization/config/optuna_config.py:205
password: str = "AdminAdmin"  # ⚠️ HARDCODED PASSWORD
```

**Required Fix:**
```python
import os

@dataclass
class StorageConfig:
    host: str = os.getenv('POSTGRES_HOST', 'localhost')
    port: int = int(os.getenv('POSTGRES_PORT', '5433'))
    database: str = os.getenv('POSTGRES_DB', 'optuna_optimization')
    username: str = os.getenv('POSTGRES_USER', 'postgres')
    password: str = os.getenv('POSTGRES_PASSWORD')  # Required env var
```

**Steps to Fix:**
1. Create `.env` file in project root (DO NOT COMMIT):
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=optuna_optimization
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your_secure_password_here>
```

2. Update `.gitignore` to exclude `.env` files:
```bash
echo ".env" >> .gitignore
echo "*.env" >> .gitignore
```

3. Create `.env.example` template for deployment:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=optuna_optimization
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change_me_in_production
```

4. Update deployment documentation:
```markdown
## Environment Variables Required

Before running optimization, create a `.env` file with:
- POSTGRES_HOST: PostgreSQL server host
- POSTGRES_PORT: PostgreSQL server port (default: 5433)
- POSTGRES_DB: Database name (default: optuna_optimization)
- POSTGRES_USER: Database username
- POSTGRES_PASSWORD: Database password (REQUIRED)
```

5. Rotate production database password:
```sql
-- Connect to PostgreSQL as admin
ALTER USER postgres WITH PASSWORD 'new_secure_password_here';
```

**Verification:**
```bash
# Test that credentials are loaded from environment
python -c "from TopStepB.optimization.config.optuna_config import StorageConfig; print(StorageConfig().get_database_url())"
```

---

## Pre-Deployment Checklist

### Security ✅/⚠️
- [ ] **CRITICAL:** Database credentials externalized to environment variables
- [ ] `.env` file created (not committed)
- [ ] `.env.example` template created
- [ ] `.gitignore` includes `.env` files
- [ ] Production database password rotated
- [x] No SQL injection vulnerabilities
- [x] Input validation present
- [x] Error messages don't leak sensitive data

### Code Quality ✅
- [x] All 101 tests passing
- [x] Zero application warnings
- [x] No TODOs/FIXMEs/HACKs
- [x] Type hints present
- [x] Documentation complete
- [x] 232+ lines dead code removed

### Performance ✅
- [x] 2289x indicator speedup achieved
- [x] 10-50x overall optimization speedup
- [x] Memory usage under 1500MB limit
- [x] Cache hit rate 100%
- [x] No memory leaks detected

### Architecture ✅
- [x] Optuna + VectorBT integration working
- [x] IndicatorCache properly integrated
- [x] BaseStrategy caching methods implemented
- [x] Loose coupling maintained
- [x] Backward compatibility preserved

### Deployment Preparation ⚠️
- [ ] Environment variables documented
- [ ] `.env.example` template provided
- [ ] Database credentials externalized
- [x] README updated
- [x] Dependencies specified
- [x] CLI interface stable

---

## Quick Deployment Guide

### 1. Local Testing (Development)
```bash
# Create .env file
cat > .env << EOF
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=optuna_optimization
POSTGRES_USER=postgres
POSTGRES_PASSWORD=AdminAdmin
EOF

# Run tests
python -m pytest tests/ -v

# Test single optimization
python -m TopStepB.optimization.engine \
    --strategy bollinger_squeeze \
    --symbol MES \
    --timeframe 1m \
    --max-trials 10
```

### 2. AWS EC2 Deployment (Production)
```bash
# 1. Upload code to EC2
scp -r TopStepB/ ubuntu@<ec2-instance>:/home/ubuntu/

# 2. SSH to instance
ssh ubuntu@<ec2-instance>

# 3. Install dependencies
cd /home/ubuntu/TopStepB
pip install -r requirements.txt

# 4. Create production .env file
cat > .env << EOF
POSTGRES_HOST=<rds-endpoint>
POSTGRES_PORT=5432
POSTGRES_DB=optuna_optimization
POSTGRES_USER=optuna_user
POSTGRES_PASSWORD=<secure_password>
EOF

# 5. Verify database connection
python -c "from TopStepB.optimization.config.optuna_config import get_optimization_config; print(get_optimization_config().storage.get_database_url())"

# 6. Run optimization
nohup python -m TopStepB.optimization.engine \
    --strategy bollinger_squeeze \
    --symbol MES \
    --timeframe 1m \
    --max-trials 50000 \
    --max-workers 0 \
    > optimization.log 2>&1 &
```

### 3. Monitoring
```bash
# Watch logs
tail -f optimization.log

# Check database
psql -h <rds-endpoint> -U optuna_user -d optuna_optimization
SELECT study_name, COUNT(*) FROM trials GROUP BY study_name;

# Monitor memory
watch -n 5 'ps aux | grep python | grep -v grep'
```

---

## Performance Expectations

### Single Worker (Baseline)
- Trial duration: 2-5 seconds (50k bars)
- Trials/hour: 720-1800
- 50,000 trials: 28-70 hours

### 16 Workers (AWS c5.9xlarge)
- Trial duration: 2-5 seconds (unchanged)
- Trials/hour: 11,520-28,800
- 50,000 trials: 1.7-4.3 hours

### Memory Requirements
- Base Python: 50 MB
- Per trial: 450 MB
- 16 workers: ~7.2 GB (fits in 16 GB instance)

---

## Rollback Procedure

If issues occur, rollback is simple:

```bash
# 1. Stop optimization
pkill -f "TopStepB.optimization.engine"

# 2. Revert to previous git commit
git checkout <previous-commit-hash>

# 3. Restart with old version
python -m TopStepB.optimization.engine ...
```

**Safe to rollback:** Yes, all external APIs unchanged.

---

## Success Criteria

Optimization is successful when:

✅ All trials complete without errors
✅ Database contains expected number of trials
✅ Memory usage stays under 1500MB per worker
✅ No worker crashes or timeouts
✅ Top parameter sets exported successfully

---

## Support & Troubleshooting

### Common Issues

**Issue 1: "No module named 'TopStepB'"**
```bash
# Fix: Add to PYTHONPATH
export PYTHONPATH=/home/ubuntu:$PYTHONPATH
```

**Issue 2: "Connection to database failed"**
```bash
# Fix: Check environment variables
printenv | grep POSTGRES
# Fix: Test database connection
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB
```

**Issue 3: "Memory limit exceeded"**
```bash
# Fix: Reduce max_workers or increase instance size
python -m TopStepB.optimization.engine --max-workers 8
```

**Issue 4: "Trial timeout"**
```bash
# Fix: Increase timeout in config
export OPTUNA_TIMEOUT_PER_TRIAL=600  # 10 minutes
```

---

## Final Sign-Off

**Deployment Approval:**
- [x] All tests passing (101/101)
- [x] Performance targets met (2289x speedup)
- [x] Architecture validated (94/100 score)
- [ ] **Security fix completed** ⚠️ REQUIRED
- [ ] Production credentials configured
- [ ] Deployment documentation reviewed

**Approved By:** Senior Code Reviewer
**Date:** 2025-12-03
**Status:** ✅ **CONDITIONAL APPROVAL** (pending security fix)

---

**⚠️ DO NOT DEPLOY TO PRODUCTION UNTIL DATABASE CREDENTIALS ARE EXTERNALIZED ⚠️**

---

## Post-Deployment Tasks

After successful deployment:

1. [ ] Monitor first 100 trials for errors
2. [ ] Verify database connection stability
3. [ ] Check memory usage patterns
4. [ ] Confirm cache hit rates remain at 100%
5. [ ] Export top parameter sets
6. [ ] Update team on deployment status
7. [ ] Schedule post-deployment review (1 week)

---

**For questions or issues, contact: blindsipher**
