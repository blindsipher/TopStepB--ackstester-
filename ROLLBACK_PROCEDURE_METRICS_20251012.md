# ROLLBACK PROCEDURE - Metrics Display System
**Emergency Rollback Guide**

## Quick Reference

**Backup Branch**: `backup/20251012_125430_metrics_display_system`
**Base Commit**: `22fbe2ce21262de196d58106c64779509f590c39`
**Date**: 2025-10-12 12:54:30

---

## EMERGENCY FULL ROLLBACK (5 MINUTES)

**USE THIS IF**: Everything is broken and you need to restore immediately.

### Step 1: Navigate to repository
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"
```

### Step 2: Verify you're in the right place
```bash
git status
git log -1 --oneline
```
Expected: Should show current changes

### Step 3: Stash any uncommitted work (SAFE)
```bash
git stash save "Emergency stash - metrics display rollback $(date +%Y%m%d_%H%M%S)"
```

### Step 4: Hard reset to backup branch
```bash
git reset --hard backup/20251012_125430_metrics_display_system
```

### Step 5: Verify rollback success
```bash
git log -1
git status
```
Expected: Should show commit 22fbe2ce21262de196d58106c64779509f590c39

### Step 6: Test the application
```bash
# Test if optimization still works
python -c "from TopStepB.optimization.objective import StatefulObjective; print('OK')"

# Test if UI loads
streamlit run src/ui/app.py --server.headless true &
sleep 5
curl http://localhost:8501 > /dev/null && echo "UI OK" || echo "UI FAIL"
```

### Step 7: Clean up if needed
```bash
# If new files were created that aren't tracked
git clean -fd -n  # Preview what will be deleted
git clean -fd     # Actually delete (only if preview looks correct)
```

---

## SELECTIVE ROLLBACK (10-15 MINUTES)

**USE THIS IF**: Only specific files are causing issues.

### Rollback Individual Files

#### Option A: Rollback objective.py only
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Check current file
git diff TopStepB/optimization/objective.py | head -20

# Restore from backup
git checkout backup/20251012_125430_metrics_display_system -- TopStepB/optimization/objective.py

# Verify
git status
python -c "from TopStepB.optimization.objective import StatefulObjective; print('Restored OK')"
```

#### Option B: Rollback database_service.py only
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Check current file
git diff src/ui/services/database_service.py | head -20

# Restore from backup
git checkout backup/20251012_125430_metrics_display_system -- src/ui/services/database_service.py

# Verify
git status
python -c "from src.ui.services.database_service import DatabaseService; print('Restored OK')"
```

#### Option C: Rollback app.py only
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Check current file
git diff src/ui/app.py | head -20

# Restore from backup
git checkout backup/20251012_125430_metrics_display_system -- src/ui/app.py

# Verify
git status
```

#### Option D: Remove new metrics_dashboard.py
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# If committed
git rm src/ui/components/metrics_dashboard.py

# If not committed
rm src/ui/components/metrics_dashboard.py

# Verify
git status
```

#### Option E: Rollback formatters.py only
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Restore from backup
git checkout backup/20251012_125430_metrics_display_system -- src/ui/utils/formatters.py

# Verify
git status
```

### After Selective Rollback

```bash
# Review all changes
git status
git diff

# Test the specific component you rolled back
# (Run appropriate tests based on what was rolled back)

# If satisfied, commit the rollback
git add .
git commit -m "rollback: Revert metrics display changes from [specific file]"
```

---

## COMMIT-BASED ROLLBACK (15-20 MINUTES)

**USE THIS IF**: Changes are committed and you want to undo specific commits while preserving history.

### Step 1: Identify commits to revert
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# View commits since backup
git log backup/20251012_125430_metrics_display_system..HEAD --oneline

# Example output:
# a1b2c3d Add metrics dashboard component
# e4f5g6h Update database service with metric queries
# i7j8k9l Enhance objective.py with metric storage
```

### Step 2: Revert commits (newest to oldest)
```bash
# Revert most recent commit first
git revert a1b2c3d --no-edit

# Then revert next commit
git revert e4f5g6h --no-edit

# Then revert oldest commit
git revert i7j8k9l --no-edit
```

### Step 3: Handle conflicts (if any)
```bash
# If conflicts occur
git status  # See conflicted files

# Edit conflicted files to resolve
# Look for <<<<<<< markers

# After resolving
git add <resolved_files>
git revert --continue
```

### Step 4: Verify revert
```bash
git log --oneline | head -5
git diff backup/20251012_125430_metrics_display_system
```

### Step 5: Test application
```bash
# Run tests to ensure everything works
pytest tests/ -v
```

---

## INTERACTIVE ROLLBACK (Advanced Users)

**USE THIS IF**: You want fine-grained control over what gets rolled back.

### Using Interactive Rebase
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Start interactive rebase from backup point
git rebase -i backup/20251012_125430_metrics_display_system

# In editor, change 'pick' to 'drop' for commits you want to remove
# Or 'edit' to modify commits
# Save and exit

# If conflicts occur
git status
# Resolve conflicts
git add <resolved_files>
git rebase --continue
```

---

## VERIFICATION AFTER ROLLBACK

### Step 1: Verify git state
```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Check current commit
git log -1 --format="%H %s"

# Compare to backup
git diff backup/20251012_125430_metrics_display_system
```
Expected: No differences (for full rollback) or only expected differences (for selective)

### Step 2: Verify file integrity
```bash
# Check file hashes match backup
powershell -Command "Get-FileHash 'TopStepB/optimization/objective.py' -Algorithm SHA256"
# Expected: E2FBCCBF0BF985B604A8337B0F436AEC57A83E01469EEF38EC54C878BC64BA44

powershell -Command "Get-FileHash 'src/ui/services/database_service.py' -Algorithm SHA256"
# Expected: 24111E39A137495AAE87506151E8900756BA47D322CE0C4152536FD8CB5AC33B

powershell -Command "Get-FileHash 'src/ui/app.py' -Algorithm SHA256"
# Expected: C8AC6D4D1363FC071D40AF1DA185A87B79E587356ADB07AD0D1BFCB14429BE13
```

### Step 3: Verify Python imports
```bash
# Test objective.py
python -c "from TopStepB.optimization.objective import StatefulObjective; print('objective.py: OK')"

# Test database_service.py
python -c "from src.ui.services.database_service import DatabaseService; print('database_service.py: OK')"

# Test app.py (basic import)
python -c "import sys; sys.path.insert(0, 'src'); from ui import app; print('app.py: OK')"
```

### Step 4: Run functional tests
```bash
# If you have tests
pytest tests/ -v -k "test_objective or test_database"

# Quick smoke test
python -m TopStepB.optimization.objective --help 2>/dev/null && echo "CLI OK" || echo "No CLI"
```

### Step 5: Test UI (optional)
```bash
# Start UI in background
streamlit run src/ui/app.py --server.headless true &
STREAMLIT_PID=$!

# Wait for startup
sleep 10

# Test if accessible
curl -s http://localhost:8501 > /dev/null && echo "UI: RUNNING" || echo "UI: FAILED"

# Kill test server
kill $STREAMLIT_PID
```

---

## ROLLBACK DECISION TREE

```
Is the system completely broken?
├─ YES → Use EMERGENCY FULL ROLLBACK
└─ NO → Continue

Is only one component failing?
├─ YES → Use SELECTIVE ROLLBACK for that file
└─ NO → Continue

Do you need to preserve git history?
├─ YES → Use COMMIT-BASED ROLLBACK (git revert)
└─ NO → Use EMERGENCY FULL ROLLBACK (git reset)

Do you want fine-grained control?
├─ YES → Use INTERACTIVE ROLLBACK (git rebase -i)
└─ NO → Use COMMIT-BASED ROLLBACK
```

---

## COMMON ISSUES & SOLUTIONS

### Issue 1: "Cannot rollback - uncommitted changes"
```bash
# Solution: Stash changes first
git stash save "Before rollback stash"
# Then proceed with rollback
# Retrieve later if needed: git stash pop
```

### Issue 2: "File conflicts during rollback"
```bash
# Solution: Use force option
git checkout backup/20251012_125430_metrics_display_system -- <file> --force

# Or reset completely
git reset --hard backup/20251012_125430_metrics_display_system
```

### Issue 3: "New files not tracked by git"
```bash
# Solution: Clean untracked files
git clean -fd -n  # Preview
git clean -fd     # Execute (BE CAREFUL!)
```

### Issue 4: "Database has new data that will be lost"
```bash
# Solution: Export database first
pg_dump -h localhost -p 5433 -U postgres optuna_optimization > backup_db.sql

# Then proceed with rollback
# Restore later if needed: psql -h localhost -p 5433 -U postgres optuna_optimization < backup_db.sql
```

### Issue 5: "UI won't start after rollback"
```bash
# Solution: Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Restart UI
streamlit run src/ui/app.py
```

---

## POST-ROLLBACK CHECKLIST

After completing rollback, verify:

- [ ] Git shows correct commit (22fbe2ce21262de196d58106c64779509f590c39 for full rollback)
- [ ] No unexpected files in git status
- [ ] Python imports work without errors
- [ ] File hashes match backup (for full rollback)
- [ ] Application starts successfully
- [ ] No errors in application logs
- [ ] Existing tests pass
- [ ] Database queries work correctly
- [ ] UI loads without errors (if applicable)
- [ ] Change log updated with rollback entry

---

## DOCUMENTATION AFTER ROLLBACK

### Update Change Log
```bash
# Add entry to change log
echo "## Rollback: Metrics Display System" >> logs/change_log_202510.md
echo "**Date**: $(date +%Y-%m-%d\ %H:%M:%S)" >> logs/change_log_202510.md
echo "**Reason**: [Describe reason for rollback]" >> logs/change_log_202510.md
echo "**Commit After Rollback**: $(git rev-parse HEAD)" >> logs/change_log_202510.md
echo "**Files Affected**: [List files rolled back]" >> logs/change_log_202510.md
echo "" >> logs/change_log_202510.md
```

### Create Rollback Report
```bash
# Generate report
cat > ROLLBACK_REPORT_$(date +%Y%m%d_%H%M%S).md <<EOF
# Rollback Report

**Date**: $(date +%Y-%m-%d\ %H:%M:%S)
**Rollback Type**: [Full/Selective/Commit-based]
**Reason**: [Describe reason]

## Files Rolled Back
- [List files]

## Current State
- Commit: $(git rev-parse HEAD)
- Branch: $(git branch --show-current)

## Verification
- [ ] Tests pass
- [ ] Application starts
- [ ] No errors

## Next Steps
- [What to do next]
EOF
```

---

## SUPPORT INFORMATION

**Backup Location**:
- Branch: backup/20251012_125430_metrics_display_system
- Commit: 22fbe2ce21262de196d58106c64779509f590c39

**File Checksums (SHA256)**:
- objective.py: E2FBCCBF0BF985B604A8337B0F436AEC57A83E01469EEF38EC54C878BC64BA44
- database_service.py: 24111E39A137495AAE87506151E8900756BA47D322CE0C4152536FD8CB5AC33B
- app.py: C8AC6D4D1363FC071D40AF1DA185A87B79E587356ADB07AD0D1BFCB14429BE13
- formatters.py: A816E00780FE768740D3DEF826206A3AF74B295BF1D4D5472B29960EF78C7FD3

**Protection Summary**: PROTECTION_SUMMARY_METRICS_DISPLAY_20251012.md

---

**REMEMBER**: Always verify changes with `git diff` before finalizing rollback!
