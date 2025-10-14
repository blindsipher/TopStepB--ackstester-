# ROLLBACK PROCEDURE
## Validation Configuration CLI Argument Fix
**Created:** 2025-10-13 08:37:00 UTC
**Guardian:** Senior Software Development Guardian
**Risk Level:** MEDIUM (Critical pipeline orchestration files)

---

## PRE-MODIFICATION STATE

### System State
- **Working Directory:** C:\Users\salte\ClaudeProjects\TopStepB--ackstester-
- **Branch:** fix-walk-forward-aggregation
- **Base Commit:** 970590a8b351a2d57a64e602db0ea97028ae9528
- **Base Commit Date:** 2025-10-12 20:12:39 +0100
- **Base Commit Message:** fix: resolve import path issues preventing optimization launches

### Files to be Modified

#### File 1: TopStepB/app/core/config_collector.py
- **Full Path:** C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\TopStepB\app\core\config_collector.py
- **Pre-modification Line Count:** 450
- **Git Object SHA1:** 9fecb80234b129dd99ff12691270dc79e8cc7348
- **Backup Location:** backup/validation_config_fix_20251013/config_collector.py.backup
- **Backup SHA256:** 356cff6cfcf6ad4e9e57906438ec564f2ad5ba3ef41b4282591d21ed11359de7

#### File 2: src/ui/services/pipeline_service.py
- **Full Path:** C:\Users\salte\ClaudeProjects\TopStepB--ackstester-\src\ui\services\pipeline_service.py
- **Pre-modification Line Count:** 207
- **Git Object SHA1:** 605f0935f991f292af22cd6292d7fa9e5a5c7cf6
- **Backup Location:** backup/validation_config_fix_20251013/pipeline_service.py.backup
- **Backup SHA256:** 1aeb7e3cca0a70f365494c82a907481eb644f4b140d69c106125836b31277e56

### Backup Branch
- **Branch Name:** backup/20251013_validation_config_fix_pre
- **Backup Commit:** d95f7672d42952116a15cd9024bb4ab69a5dc4f5
- **Backup Date:** 2025-10-13 08:36:47 +0100

---

## BUG DESCRIPTION

**Issue:** Validation configuration does not flow from UI through CLI arguments to pipeline state.

**Root Cause:**
1. pipeline_service.py only passes validation_tests as single comma-separated string (line 114-115)
2. config_collector.py parses this into a list but lacks CLI arguments for detailed validation parameters:
   - Permutation test counts and thresholds
   - Monte Carlo simulation counts
   - Noise injection sigma values
   - Individual test enable/disable flags

**Impact:** Validation phase receives only default configuration regardless of UI settings.

**Planned Changes:**
1. Add ~15 CLI arguments to config_collector.py for validation configuration
2. Update pipeline_service.py subprocess command builder to pass all validation settings
3. Ensure validation settings flow: UI → CLI args → PipelineState → Validation engine

---

## ROLLBACK PROCEDURE

### Method 1: Git Branch Rollback (RECOMMENDED)

**When to use:** If git history is clean and no other changes have been made.

```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Verify current location
git log -1 --oneline

# Switch to backup branch
git checkout backup/20251013_validation_config_fix_pre

# Verify we're on backup
git log -1 --format="%H %s"
# Expected: d95f7672d42952116a15cd9024bb4ab69a5dc4f5 Backup before validation config CLI argument fix

# Reset working branch to backup state
git checkout fix-walk-forward-aggregation
git reset --hard backup/20251013_validation_config_fix_pre

# Verify rollback success
git log -1 --oneline
git status
```

**Verification:**
```bash
# Check file hashes match pre-modification state
git hash-object "TopStepB/app/core/config_collector.py"  # Should be 9fecb80234b129dd99ff12691270dc79e8cc7348
git hash-object "src/ui/services/pipeline_service.py"    # Should be 605f0935f991f292af22cd6292d7fa9e5a5c7cf6

# Check line counts
wc -l "TopStepB/app/core/config_collector.py"  # Should be 450
wc -l "src/ui/services/pipeline_service.py"    # Should be 207
```

### Method 2: Physical File Restore

**When to use:** If git method fails or other changes need to be preserved.

```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Verify backups exist
ls -lh backup/validation_config_fix_20251013/

# Restore files
cp "backup/validation_config_fix_20251013/config_collector.py.backup" "TopStepB/app/core/config_collector.py"
cp "backup/validation_config_fix_20251013/pipeline_service.py.backup" "src/ui/services/pipeline_service.py"

# Verify restoration
sha256sum "TopStepB/app/core/config_collector.py"
# Expected: 356cff6cfcf6ad4e9e57906438ec564f2ad5ba3ef41b4282591d21ed11359de7

sha256sum "src/ui/services/pipeline_service.py"
# Expected: 1aeb7e3cca0a70f365494c82a907481eb644f4b140d69c106125836b31277e56
```

### Method 3: Git Revert (If Changes Already Committed)

**When to use:** If changes were committed and you want to preserve history.

```bash
cd "C:\Users\salte\ClaudeProjects\TopStepB--ackstester-"

# Find the commit hash of the change (will be known after modification)
git log --oneline -10

# Revert the specific commit
git revert <COMMIT_HASH>

# This creates a new commit that undoes the changes
```

---

## ROLLBACK VERIFICATION CHECKLIST

After executing rollback procedure, verify:

- [ ] File line counts match pre-modification state
  - [ ] config_collector.py = 450 lines
  - [ ] pipeline_service.py = 207 lines

- [ ] Git object hashes match (if using git method)
  - [ ] config_collector.py: 9fecb80234b129dd99ff12691270dc79e8cc7348
  - [ ] pipeline_service.py: 605f0935f991f292af22cd6292d7fa9e5a5c7cf6

- [ ] SHA256 checksums match (if using file restore)
  - [ ] config_collector.py: 356cff6cfcf6ad4e9e57906438ec564f2ad5ba3ef41b4282591d21ed11359de7
  - [ ] pipeline_service.py: 1aeb7e3cca0a70f365494c82a907481eb644f4b140d69c106125836b31277e56

- [ ] System functionality test
  - [ ] Import config_collector: `python -c "from TopStepB.app.core import config_collector; print('OK')"`
  - [ ] Import pipeline_service: `python -c "from src.ui.services.pipeline_service import PipelineService; print('OK')"`
  - [ ] Run help: `python TopStepB/main_runner.py --help` (should show original args)

- [ ] Git status clean (no unexpected changes)

---

## EMERGENCY CONTACT / ESCALATION

If rollback fails:

1. **DO NOT PANIC** - All backups are secure
2. **DO NOT make additional changes**
3. Check backup branch exists: `git branch | grep backup/20251013`
4. Check physical backups exist: `ls -lh backup/validation_config_fix_20251013/`
5. Consult this document's verification steps carefully
6. If still stuck, the original files are preserved in git history at commit 970590a8b351a2d57a64e602db0ea97028ae9528

---

## POST-ROLLBACK ACTIONS

After successful rollback:

1. Document why rollback was necessary
2. Update change log with rollback entry
3. Analyze what went wrong with the modification
4. Create revised implementation plan if re-attempting fix
5. Inform stakeholders if change was in production

---

## NOTES

- Backup branch will be retained for 30 days minimum
- Physical backup files in backup/ directory should not be deleted until change is verified stable
- This rollback procedure was generated BEFORE any modifications were made
- All checksums and hashes are from pre-modification state
- Test the rollback procedure in development environment first if possible

---

## CHANGE LOG REFERENCE

All changes related to this modification should be documented in:
- logs/change_log_202510.md (monthly change log)
- logs/aggregator.log (daily activity log)

---

**Document Status:** ACTIVE - Ready for use if rollback needed
**Last Updated:** 2025-10-13 08:37:00 UTC
**Approver:** Senior Software Development Guardian
