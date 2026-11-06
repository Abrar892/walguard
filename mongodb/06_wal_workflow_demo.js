// ============================================================
// FILE: 06_wal_workflow_demo.js
// PURPOSE: Step-by-step simulation of the full WAL lifecycle
//          in mongosh — demonstrates the exact sequence used
//          by the Python transaction_manager.py
//
// WORKFLOW SIMULATED:
//   Normal commit   → UNCOMMITTED → COMMITTED
//   Rollback        → UNCOMMITTED → ROLLED_BACK
//   Crash (no end)  → UNCOMMITTED stays → Recovery UNDO
//
// HOW TO RUN: Execute each STEP block one at a time in mongosh
// ============================================================

use("bank_recovery_logs");

print("=".repeat(60));
print(" WAL Workflow Live Demo");
print(" Run each STEP block individually for the viva demo");
print("=".repeat(60));


// ─────────────────────────────────────────
// STEP 0: Clean slate for demo
// ─────────────────────────────────────────
db.wal_logs.deleteMany({ session_id: "DEMO_SESSION" });
db.recovery_logs.deleteMany({ recovery_session: "DEMO_RECOVERY" });
print("\n  [STEP 0] Demo slate cleared. Ready for demo.");


// ─────────────────────────────────────────
// STEP 1: SCENARIO A — Normal Transaction (ends in COMMIT)
//
//  Timeline:
//  [1a] WAL log written (status=UNCOMMITTED)  ← MongoDB
//  [1b] PostgreSQL balance updated            ← PostgreSQL
//  [1c] WAL log updated (status=COMMITTED)   ← MongoDB
// ─────────────────────────────────────────
print("\n── STEP 1A: WAL Log written BEFORE PostgreSQL update ──");

const txnA_logId = 201;
const txnA_txnId = 201;

// [1a] WRITE WAL FIRST — this is the Write-Ahead Log principle
db.wal_logs.insertOne({
    log_id:           txnA_logId,
    transaction_id:   txnA_txnId,
    session_id:       "DEMO_SESSION",
    operation:        "UPDATE",
    table_name:       "Account",
    account_id:       1,
    transaction_type: "DEPOSIT",
    old_balance:      10000.00,
    new_balance:      12000.00,
    amount:            2000.00,
    status:           "UNCOMMITTED",      // ← Written BEFORE PG update
    timestamp:        new Date(),
    notes:            "DEMO: WAL written — PostgreSQL update not yet applied"
});

print("  → WAL log written with status=UNCOMMITTED");
print("  → [NOW IN REAL SYSTEM: PostgreSQL UPDATE Account SET balance=12000 WHERE account_id=1]");

// [1b] PostgreSQL update happens here (simulated — happens in Python)
// UPDATE Account SET balance = 12000.00 WHERE account_id = 1;

print("\n── STEP 1B: PostgreSQL update complete → Update WAL to COMMITTED ──");

// [1c] UPDATE WAL log status to COMMITTED
db.wal_logs.updateOne(
    { log_id: txnA_logId, session_id: "DEMO_SESSION" },
    { $set: { status: "COMMITTED", notes: "DEMO: Transaction committed successfully" } }
);

print("  → WAL log updated to status=COMMITTED");
print("  → Transaction A complete. Balance: 10000 → 12000");
printjson(db.wal_logs.findOne({ log_id: txnA_logId }, { _id: 0 }));


// ─────────────────────────────────────────
// STEP 2: SCENARIO B — Rollback
//
//  Timeline:
//  [2a] WAL log written (status=UNCOMMITTED)
//  [2b] PostgreSQL update FAILS (constraint violation)
//  [2c] ROLLBACK called → WAL log updated to ROLLED_BACK
// ─────────────────────────────────────────
print("\n── STEP 2: Rollback Scenario ──");

const txnB_logId = 202;
const txnB_txnId = 202;

// [2a] WAL written first
db.wal_logs.insertOne({
    log_id:           txnB_logId,
    transaction_id:   txnB_txnId,
    session_id:       "DEMO_SESSION",
    operation:        "UPDATE",
    table_name:       "Account",
    account_id:       4,
    transaction_type: "WITHDRAWAL",
    old_balance:      15000.00,
    new_balance:          0.00,
    amount:           20000.00,
    status:           "UNCOMMITTED",
    timestamp:        new Date(),
    notes:            "DEMO: Withdrawal attempt — insufficient funds"
});

print("  → WAL log written (UNCOMMITTED)");
print("  → [NOW: PostgreSQL rejects — balance constraint violation]");
print("  → [Python catches exception → ROLLBACK called]");

// [2c] Update WAL to ROLLED_BACK
db.wal_logs.updateOne(
    { log_id: txnB_logId, session_id: "DEMO_SESSION" },
    { $set: { status: "ROLLED_BACK", notes: "DEMO: Insufficient funds — rolled back" } }
);

print("  → WAL log updated to status=ROLLED_BACK");
print("  → PG balance unchanged at 15000.00");
printjson(db.wal_logs.findOne({ log_id: txnB_logId }, { _id: 0 }));


// ─────────────────────────────────────────
// STEP 3: SCENARIO C — Crash Simulation
//
//  Timeline:
//  [3a] WAL log written (status=UNCOMMITTED)
//  [3b] PostgreSQL update partially applied
//  [3c] *** CRASH *** — nothing more executes
//  Result: WAL log stays UNCOMMITTED → Recovery Manager detects this
// ─────────────────────────────────────────
print("\n── STEP 3: Crash Simulation ──");

const txnC_logId = 203;
const txnC_txnId = 203;

// [3a] WAL written
db.wal_logs.insertOne({
    log_id:           txnC_logId,
    transaction_id:   txnC_txnId,
    session_id:       "DEMO_SESSION",
    operation:        "UPDATE",
    table_name:       "Account",
    account_id:       3,
    transaction_type: "WITHDRAWAL",
    old_balance:      22000.00,
    new_balance:      19000.00,
    amount:            3000.00,
    status:           "UNCOMMITTED",
    timestamp:        new Date(),
    notes:            "DEMO: WAL written — CRASH will happen before COMMIT"
});

print("  → WAL log written (UNCOMMITTED)");
print("  → [NOW: PostgreSQL UPDATE applied: balance = 19000]");
print("  → *** CRASH SIMULATED — Python process terminated ***");
print("  → WAL log remains UNCOMMITTED (never updated to COMMITTED)");
print("  → PostgreSQL may show 19000, but log says UNCOMMITTED");
printjson(db.wal_logs.findOne({ log_id: txnC_logId }, { _id: 0 }));


// ─────────────────────────────────────────
// STEP 4: RECOVERY — Analysis Phase
//   Scan for UNCOMMITTED logs → these are crash victims
// ─────────────────────────────────────────
print("\n── STEP 4: Recovery — Analysis Phase ──");

const crashedLogs = db.wal_logs.find(
    { status: "UNCOMMITTED", session_id: "DEMO_SESSION" },
    { _id: 0, log_id: 1, transaction_id: 1, account_id: 1,
      old_balance: 1, new_balance: 1 }
).toArray();

print(`  → Found ${crashedLogs.length} UNCOMMITTED logs (crash victims):`);
crashedLogs.forEach(l => printjson(l));


// ─────────────────────────────────────────
// STEP 5: RECOVERY — UNDO Phase
//   For each UNCOMMITTED log: restore old_balance in PostgreSQL
//   Then update WAL log status → ROLLED_BACK
// ─────────────────────────────────────────
print("\n── STEP 5: Recovery — UNDO Phase ──");

crashedLogs.forEach(log => {
    print(`  → UNDO transaction_id=${log.transaction_id}: restore account_id=${log.account_id} to balance=${log.old_balance}`);
    print(`     [SQL]: UPDATE Account SET balance = ${log.old_balance} WHERE account_id = ${log.account_id}`);

    // Mark WAL log as ROLLED_BACK
    db.wal_logs.updateOne(
        { log_id: log.log_id },
        { $set: { status: "ROLLED_BACK", notes: "UNDO applied by Recovery Manager" } }
    );

    // Write recovery_log entry
    db.recovery_logs.insertOne({
        recovery_id:             300 + log.log_id,
        recovery_type:           "UNDO",
        transaction_id:          log.transaction_id,
        account_id:              log.account_id,
        balance_before_recovery: log.new_balance,
        balance_after_recovery:  log.old_balance,
        reason:                  "CRASH_DETECTED",
        recovered_at:            new Date(),
        recovery_session:        "DEMO_RECOVERY",
        notes:                   `UNDO: account_id=${log.account_id} restored from ${log.new_balance} → ${log.old_balance}`
    });
});

print("  → UNDO complete. All accounts restored.");


// ─────────────────────────────────────────
// STEP 6: VERIFY — Check final state
// ─────────────────────────────────────────
print("\n── STEP 6: Final Verification ──");

print("  WAL logs (DEMO_SESSION) — final status:");
db.wal_logs.find(
    { session_id: "DEMO_SESSION" },
    { _id: 0, log_id: 1, transaction_id: 1, account_id: 1, status: 1 }
).forEach(doc => printjson(doc));

print("\n  Recovery logs (DEMO_RECOVERY):");
db.recovery_logs.find(
    { recovery_session: "DEMO_RECOVERY" },
    { _id: 0, recovery_id: 1, recovery_type: 1, transaction_id: 1,
      account_id: 1, balance_before_recovery: 1, balance_after_recovery: 1 }
).forEach(doc => printjson(doc));

print("\n" + "=".repeat(60));
print(" WAL Workflow Demo Complete!");
print(" Key takeaway: WAL logs in MongoDB are written FIRST,");
print(" allowing Recovery Manager to UNDO/REDO after any crash.");
print("=".repeat(60) + "\n");
