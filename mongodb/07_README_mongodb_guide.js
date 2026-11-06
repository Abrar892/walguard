// ============================================================
// FILE: 07_README_mongodb_guide.js
// PURPOSE: Setup guide as a runnable script with full comments
// PROJECT: ADBMS Final Project - Log-Based Recovery System
// ============================================================

/*
╔══════════════════════════════════════════════════════════════╗
║         MONGODB SETUP GUIDE — LOG-BASED RECOVERY SYSTEM       ║
║               ADBMS Final Project                             ║
╚══════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════
 PREREQUISITES
═══════════════════════════════════════════════════════════════
  • MongoDB 6.0+ installed and running (localhost:27017)
  • mongosh installed (MongoDB Shell)
  • No authentication required for local setup
  • OR: MongoDB Compass installed (GUI alternative)

═══════════════════════════════════════════════════════════════
 DATABASE & COLLECTIONS OVERVIEW
═══════════════════════════════════════════════════════════════

  Database Name: bank_recovery_logs

  Collections:
  ┌─────────────────┬────────────────────────────────────────┐
  │ Collection      │ Purpose                                │
  ├─────────────────┼────────────────────────────────────────┤
  │ wal_logs        │ Write-Ahead Log — written BEFORE PG    │
  │                 │ update. Core of WAL logging concept.   │
  ├─────────────────┼────────────────────────────────────────┤
  │ recovery_logs   │ Audit trail of UNDO/REDO actions       │
  │                 │ taken by the Recovery Manager          │
  ├─────────────────┼────────────────────────────────────────┤
  │ crash_log       │ One entry per crash event — stores     │
  │                 │ which transactions were uncommitted    │
  ├─────────────────┼────────────────────────────────────────┤
  │ system_config   │ Metadata: log counters, session IDs    │
  └─────────────────┴────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
 STEP-BY-STEP SETUP
═══════════════════════════════════════════════════════════════

  METHOD A: Using mongosh CLI (Recommended)
  ─────────────────────────────────────────
  Open PowerShell or Command Prompt and run:

    Step 1 — Verify MongoDB is running:
      mongosh --eval "db.runCommand({ping:1})"

    Step 2 — Create database and collections:
      mongosh < 01_setup_database.js

    Step 3 — Insert sample WAL logs:
      mongosh < 02_sample_wal_logs.js

    Step 4 — Insert recovery and crash logs:
      mongosh < 03_recovery_logs.js

    Step 5 — Explore data with queries:
      mongosh < 04_queries.js

    Step 6 — (Optional) Run WAL workflow demo:
      mongosh < 06_wal_workflow_demo.js


  METHOD B: Using MongoDB Compass (GUI)
  ──────────────────────────────────────
    Step 1 — Open MongoDB Compass
    Step 2 — Connect: mongodb://localhost:27017
    Step 3 — Open "MONGOSH" tab at the bottom
    Step 4 — Copy and paste each .js file content into the shell
    Step 5 — Press Enter to execute


  METHOD C: Copy-paste into mongosh interactive
  ──────────────────────────────────────────────
    $ mongosh
    > use("bank_recovery_logs")
    > // Paste content of each file one at a time

═══════════════════════════════════════════════════════════════
 FILE EXECUTION ORDER
═══════════════════════════════════════════════════════════════

  Order  File                      Purpose
  ─────  ────────────────────────  ────────────────────────────
  [1]    01_setup_database.js      Create DB + collections + indexes
  [2]    02_sample_wal_logs.js     Insert WAL log sample documents
  [3]    03_recovery_logs.js       Insert recovery + crash log docs
  [4]    04_queries.js             Explore all data (run anytime)
  [5]    06_wal_workflow_demo.js   Live step-by-step WAL demo
  [REF]  05_sample_documents.json  Reference document — do not run

═══════════════════════════════════════════════════════════════
 DOCUMENT STRUCTURE REFERENCE
═══════════════════════════════════════════════════════════════

  wal_logs document:
  ──────────────────
  {
    log_id          : Int    — sequential log number
    transaction_id  : Int    — links to PG Transaction_Record
    session_id      : String — application session identifier
    operation       : String — UPDATE | INSERT | DELETE
    table_name      : String — which PG table (usually "Account")
    account_id      : Int    — links to PG Account
    transaction_type: String — DEPOSIT|WITHDRAWAL|TRANSFER_IN|OUT
    old_balance     : Double — balance BEFORE (used in UNDO)
    new_balance     : Double — balance AFTER  (used in REDO)
    amount          : Double — transaction amount
    status          : String — UNCOMMITTED | COMMITTED | ROLLED_BACK
    timestamp       : Date   — when log was written to MongoDB
    notes           : String — optional context
  }

  STATUS LIFECYCLE:
  ─────────────────
  Written → UNCOMMITTED
     │
     ├─ PG update succeeds + COMMIT → COMMITTED
     ├─ PG constraint fails + ROLLBACK → ROLLED_BACK
     └─ CRASH (no commit/rollback) → stays UNCOMMITTED
                                      ↑ Recovery UNDO target

  recovery_logs document:
  ───────────────────────
  {
    recovery_id             : Int    — sequential ID
    recovery_type           : String — UNDO | REDO
    transaction_id          : Int    — which txn was affected
    account_id              : Int    — which account was fixed
    balance_before_recovery : Double — PG balance before recovery
    balance_after_recovery  : Double — PG balance after recovery
    reason                  : String — CRASH_DETECTED|MANUAL_ROLLBACK|COMMIT_LOSS
    recovered_at            : Date   — when recovery was applied
    recovery_session        : String — groups recovery actions
    notes                   : String — what was done
  }

  crash_log document:
  ────────────────────
  {
    crash_id                     : Int     — sequential crash ID
    crash_detected_at            : Date    — crash time
    crash_type                   : String  — UNEXPECTED_SHUTDOWN etc
    uncommitted_transaction_ids  : Array   — transactions to UNDO
    committed_transaction_ids    : Array   — transactions to REDO if needed
    rolled_back_transaction_ids  : Array   — already handled
    recovery_triggered           : Boolean — was recovery run?
    recovery_started_at          : Date
    recovery_completed_at        : Date
    recovery_summary             : String  — what was done
  }

═══════════════════════════════════════════════════════════════
 QUICK VERIFICATION COMMANDS (run in mongosh after setup)
═══════════════════════════════════════════════════════════════

  // List all collections
  use("bank_recovery_logs")
  db.getCollectionNames()

  // Count documents in each collection
  db.wal_logs.countDocuments()
  db.recovery_logs.countDocuments()
  db.crash_log.countDocuments()

  // Find all UNCOMMITTED (crash victims)
  db.wal_logs.find({ status: "UNCOMMITTED" })

  // Find all COMMITTED
  db.wal_logs.find({ status: "COMMITTED" })

  // Count by status
  db.wal_logs.aggregate([
      { $group: { _id: "$status", count: { $sum: 1 } } }
  ])

  // View recovery audit
  db.recovery_logs.find().sort({ recovered_at: 1 })

  // View crash event
  db.crash_log.findOne()

═══════════════════════════════════════════════════════════════
 ADBMS CONCEPTS DEMONSTRATED BY MONGODB
═══════════════════════════════════════════════════════════════

  Concept                  How MongoDB Demonstrates It
  ───────                  ───────────────────────────
  Write-Ahead Logging      Log inserted BEFORE PG update in every txn
  Undo Logging             old_balance stored → used to reverse changes
  Redo Logging             new_balance stored → used to re-apply changes
  Transaction Lifecycle    UNCOMMITTED → COMMITTED / ROLLED_BACK
  Crash Recovery           UNCOMMITTED logs = recovery targets
  Polyglot Persistence     MongoDB + PostgreSQL used together
  NoSQL Flexibility        Schema-free docs store rich metadata easily
  Log Audit Trail          recovery_logs show what Recovery Manager did
  Analysis Phase (ARIES)   Scan UNCOMMITTED logs = Analysis Phase
  Undo Phase (ARIES)       Restore old_balance for all UNCOMMITTED
  Redo Phase (ARIES)       Re-apply new_balance for COMMITTED if lost

═══════════════════════════════════════════════════════════════
 COMMON ERRORS AND FIXES
═══════════════════════════════════════════════════════════════

  ERROR: MongoServerError: Document failed validation
  FIX:   Check that all required fields are present:
         log_id, transaction_id, operation, account_id,
         old_balance, new_balance, status, timestamp
         Ensure status is one of: UNCOMMITTED|COMMITTED|ROLLED_BACK

  ERROR: MongoNetworkError: connect ECONNREFUSED 127.0.0.1:27017
  FIX:   MongoDB is not running.
         Windows: net start MongoDB
         Or: Start MongoDB Compass (it starts the service)

  ERROR: ReferenceError: use is not defined
  FIX:   You are running the file as Node.js, not mongosh.
         Always run with: mongosh < filename.js

  ERROR: 'use' is not a function
  FIX:   In mongosh interactive, use without parentheses:
         use bank_recovery_logs  (not use("bank_recovery_logs"))
         But in .js files loaded with load() or piped in:
         use("bank_recovery_logs") with quotes works correctly

╔══════════════════════════════════════════════════════════════╗
║     Good luck with your ADBMS viva and presentation!         ║
║     MongoDB demonstrates WAL, polyglot persistence,          ║
║     and flexible NoSQL log storage beautifully.               ║
╚══════════════════════════════════════════════════════════════╝
*/

use("bank_recovery_logs");
print("MongoDB bank_recovery_logs database is ready.");
print("Run db.getCollectionNames() to see all collections.");
db.getCollectionNames().forEach(n => {
    print(`  • ${n}: ${db.getCollection(n).countDocuments()} documents`);
});
