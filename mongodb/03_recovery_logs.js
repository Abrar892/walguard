// ============================================================
// FILE: 03_recovery_logs.js
// PURPOSE: Insert sample recovery_logs and crash_log documents
//          that demonstrate what the Recovery Manager produces
//          after detecting and handling a crash.
//
// WHEN THESE ARE CREATED:
//   recovery_logs → written AFTER each UNDO or REDO action
//   crash_log     → written ONCE per crash detection event
//
// HOW TO RUN:
//   mongosh < 03_recovery_logs.js
// ============================================================

use("bank_recovery_logs");

print("=".repeat(60));
print(" Inserting Recovery Log & Crash Log Documents...");
print("=".repeat(60));

// Clear existing
db.recovery_logs.deleteMany({});
db.crash_log.deleteMany({});


// ─────────────────────────────────────────
// PART 1: crash_log — The crash event record
//
// This document is written by the Recovery Manager when it
// starts up and detects uncommitted transactions in wal_logs.
// It records WHAT was found during the Analysis Phase.
// ─────────────────────────────────────────

db.crash_log.insertOne({
    crash_id:                    1,
    crash_detected_at:           new Date("2026-05-17T10:00:30Z"),
    crash_type:                  "UNEXPECTED_SHUTDOWN",
    uncommitted_transaction_ids: [108, 109, 110],   // Found in wal_logs with UNCOMMITTED
    committed_transaction_ids:   [101, 102, 103, 104, 105],
    rolled_back_transaction_ids: [106, 107],
    recovery_triggered:          true,
    recovery_started_at:         new Date("2026-05-17T10:00:45Z"),
    recovery_completed_at:       new Date("2026-05-17T10:01:05Z"),
    recovery_summary:            "UNDO applied to 3 uncommitted transactions (108, 109, 110). No REDO needed. All accounts restored to pre-crash state."
});

print("  ✓ Inserted crash_log document (crash_id: 1)");


// ─────────────────────────────────────────
// PART 2: recovery_logs — UNDO actions
//
// One recovery_log document is written for each UNDO action.
// The Recovery Manager writes these as proof of what it did.
// They correspond to wal_logs with status = "UNCOMMITTED"
// ─────────────────────────────────────────

db.recovery_logs.insertMany([

    // ── UNDO for transaction 108 (withdrawal on account 1) ──
    {
        recovery_id:             1,
        recovery_type:           "UNDO",
        transaction_id:          108,
        account_id:              1,
        balance_before_recovery: 7000.00,     // What PG showed (partial crash state)
        balance_after_recovery:  10000.00,    // Restored from wal_log.old_balance
        reason:                  "CRASH_DETECTED",
        recovered_at:            new Date("2026-05-17T10:00:50Z"),
        recovery_session:        "recovery_20260517_001",
        notes:                   "UNDO: Restored account_id=1 from 7000 → 10000 (old_balance from WAL log_id=8)"
    },

    // ── UNDO for transaction 109 (deposit on account 3) ─────
    {
        recovery_id:             2,
        recovery_type:           "UNDO",
        transaction_id:          109,
        account_id:              3,
        balance_before_recovery: 24500.00,    // Partial crash state
        balance_after_recovery:  22000.00,    // Restored to old_balance
        reason:                  "CRASH_DETECTED",
        recovered_at:            new Date("2026-05-17T10:00:55Z"),
        recovery_session:        "recovery_20260517_001",
        notes:                   "UNDO: Restored account_id=3 from 24500 → 22000 (old_balance from WAL log_id=9)"
    },

    // ── UNDO for transaction 110 (transfer on account 7) ────
    {
        recovery_id:             3,
        recovery_type:           "UNDO",
        transaction_id:          110,
        account_id:              7,
        balance_before_recovery: 1000.00,     // Partial crash state
        balance_after_recovery:  3500.00,     // Restored to old_balance
        reason:                  "CRASH_DETECTED",
        recovered_at:            new Date("2026-05-17T10:01:00Z"),
        recovery_session:        "recovery_20260517_001",
        notes:                   "UNDO: Restored account_id=7 from 1000 → 3500 (old_balance from WAL log_id=10)"
    }

]);

print("  ✓ Inserted 3 UNDO recovery_log documents");


// ─────────────────────────────────────────
// PART 3: recovery_logs — REDO actions
//
// A REDO is needed when a transaction was COMMITTED in MongoDB
// but the corresponding PostgreSQL change was lost (e.g., buffer
// not flushed before crash). The recovery manager re-applies
// new_balance from the WAL log.
//
// For this demo: simulate that transaction 105 (deposit, account 5)
// was committed in MongoDB but PG balance was not flushed.
// ─────────────────────────────────────────

db.recovery_logs.insertOne({
    recovery_id:             4,
    recovery_type:           "REDO",
    transaction_id:          105,
    account_id:              5,
    balance_before_recovery: 7000.00,     // PG showed stale pre-crash value
    balance_after_recovery:  8000.00,     // Re-applied from wal_log.new_balance
    reason:                  "COMMIT_LOSS",
    recovered_at:            new Date("2026-05-17T10:01:05Z"),
    recovery_session:        "recovery_20260517_001",
    notes:                   "REDO: Re-applied committed transaction 105 on account_id=5 (new_balance from WAL log_id=5)"
});

print("  ✓ Inserted 1 REDO recovery_log document");


// ─────────────────────────────────────────
// PART 4: Update wal_logs status after recovery
//   The UNCOMMITTED logs should be marked ROLLED_BACK
//   once UNDO has been applied — this prevents double-undo
// ─────────────────────────────────────────

const undoneIds = [108, 109, 110];

const result = db.wal_logs.updateMany(
    { transaction_id: { $in: undoneIds }, status: "UNCOMMITTED" },
    {
        $set: {
            status: "ROLLED_BACK",
            notes:  "Updated by Recovery Manager — UNDO applied"
        }
    }
);

print(`  ✓ Updated ${result.modifiedCount} UNCOMMITTED wal_logs → ROLLED_BACK`);


// ─────────────────────────────────────────
// Final state summary
// ─────────────────────────────────────────
print("\n" + "=".repeat(60));
print(" Recovery Logs — Document Summary:");
print("=".repeat(60));

print("\n  [wal_logs] by status:");
["COMMITTED", "ROLLED_BACK", "UNCOMMITTED"].forEach(s => {
    const c = db.wal_logs.countDocuments({ status: s });
    print(`    ${s.padEnd(15)}: ${c}`);
});

print("\n  [recovery_logs] by type:");
["UNDO", "REDO"].forEach(t => {
    const c = db.recovery_logs.countDocuments({ recovery_type: t });
    print(`    ${t.padEnd(10)}: ${c}`);
});

print(`\n  [crash_log]    : ${db.crash_log.countDocuments()} event(s)`);
print("\n  Run 04_queries.js to explore the data.");
print("=".repeat(60) + "\n");
