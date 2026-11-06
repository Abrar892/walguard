// ============================================================
// FILE: 02_sample_wal_logs.js
// PURPOSE: Insert realistic Write-Ahead Log (WAL) documents
//          into the wal_logs collection.
//
// CONCEPT:
//   Each document represents ONE log entry written to MongoDB
//   BEFORE the corresponding PostgreSQL update is applied.
//   This is the core Write-Ahead Logging (WAL) principle:
//     "Log first → Then update data"
//
// STATUS LIFECYCLE:
//   UNCOMMITTED → (commit) → COMMITTED
//   UNCOMMITTED → (rollback/crash) → ROLLED_BACK
//
// HOW TO RUN:
//   mongosh < 02_sample_wal_logs.js
// ============================================================

use("bank_recovery_logs");

print("=".repeat(60));
print(" Inserting Sample WAL Log Documents...");
print("=".repeat(60));

// Clear existing sample data
db.wal_logs.deleteMany({});

// ─────────────────────────────────────────
// GROUP 1: Committed Transactions (normal flow)
//   These represent successful operations:
//   WAL log written → PG updated → status set to COMMITTED
// ─────────────────────────────────────────

db.wal_logs.insertMany([

    // ── Log 1: Deposit — COMMITTED ──────────────────────────
    {
        log_id:           1,
        transaction_id:   101,
        session_id:       "sess_20260517_001",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       1,
        transaction_type: "DEPOSIT",
        old_balance:      8000.00,
        new_balance:      10000.00,
        amount:           2000.00,
        status:           "COMMITTED",
        timestamp:        new Date("2026-05-17T08:00:00Z"),
        notes:            "Initial deposit by Ali Raza — counter deposit"
    },

    // ── Log 2: Withdrawal — COMMITTED ───────────────────────
    {
        log_id:           2,
        transaction_id:   102,
        session_id:       "sess_20260517_001",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       3,
        transaction_type: "WITHDRAWAL",
        old_balance:      25000.00,
        new_balance:      22000.00,
        amount:           3000.00,
        status:           "COMMITTED",
        timestamp:        new Date("2026-05-17T08:15:00Z"),
        notes:            "Withdrawal by Sara Khan"
    },

    // ── Log 3: Transfer OUT leg — COMMITTED ─────────────────
    {
        log_id:           3,
        transaction_id:   103,
        session_id:       "sess_20260517_002",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       1,
        transaction_type: "TRANSFER_OUT",
        old_balance:      10000.00,
        new_balance:       8500.00,
        amount:            1500.00,
        status:           "COMMITTED",
        timestamp:        new Date("2026-05-17T08:30:00Z"),
        notes:            "Transfer OUT: ACC-00001 → ACC-00007"
    },

    // ── Log 4: Transfer IN leg — COMMITTED ──────────────────
    {
        log_id:           4,
        transaction_id:   104,
        session_id:       "sess_20260517_002",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       7,
        transaction_type: "TRANSFER_IN",
        old_balance:       2000.00,
        new_balance:       3500.00,
        amount:            1500.00,
        status:           "COMMITTED",
        timestamp:        new Date("2026-05-17T08:30:05Z"),
        notes:            "Transfer IN: ACC-00007 ← ACC-00001"
    },

    // ── Log 5: Deposit — COMMITTED ──────────────────────────
    {
        log_id:           5,
        transaction_id:   105,
        session_id:       "sess_20260517_003",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       5,
        transaction_type: "DEPOSIT",
        old_balance:       7000.00,
        new_balance:       8000.00,
        amount:            1000.00,
        status:           "COMMITTED",
        timestamp:        new Date("2026-05-17T09:00:00Z"),
        notes:            "Cash deposit — Fatima Siddiqui"
    }

]);

print("  ✓ Inserted 5 COMMITTED WAL log documents");


// ─────────────────────────────────────────
// GROUP 2: Rolled-Back Transactions
//   WAL log written → PG update started or blocked
//   → ROLLBACK triggered → status set to ROLLED_BACK
//   The old_balance was preserved (UNDO used old_balance)
// ─────────────────────────────────────────

db.wal_logs.insertMany([

    // ── Log 6: Insufficient Funds — ROLLED_BACK ─────────────
    {
        log_id:           6,
        transaction_id:   106,
        session_id:       "sess_20260517_004",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       4,
        transaction_type: "WITHDRAWAL",
        old_balance:      15000.00,
        new_balance:          0.00,  // Would go below 0 — caught and rolled back
        amount:           20000.00,
        status:           "ROLLED_BACK",
        timestamp:        new Date("2026-05-17T09:20:00Z"),
        notes:            "ROLLED_BACK: Insufficient funds — Ahmed Malik attempted 20000 withdrawal"
    },

    // ── Log 7: Manual cancel by operator — ROLLED_BACK ──────
    {
        log_id:           7,
        transaction_id:   107,
        session_id:       "sess_20260517_005",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       5,
        transaction_type: "DEPOSIT",
        old_balance:       8000.00,
        new_balance:      13000.00,
        amount:            5000.00,
        status:           "ROLLED_BACK",
        timestamp:        new Date("2026-05-17T09:35:00Z"),
        notes:            "ROLLED_BACK: Operator cancelled deposit manually"
    }

]);

print("  ✓ Inserted 2 ROLLED_BACK WAL log documents");


// ─────────────────────────────────────────
// GROUP 3: Uncommitted Transactions (CRASH SIMULATION)
//   These are transactions where:
//     - WAL log was written to MongoDB ✓
//     - PostgreSQL update may have partially applied ✗
//     - COMMIT or ROLLBACK never executed (crash)
//   → Recovery Manager must UNDO these
// ─────────────────────────────────────────

db.wal_logs.insertMany([

    // ── Log 8: CRASH mid-withdrawal ─────────────────────────
    {
        log_id:           8,
        transaction_id:   108,
        session_id:       "sess_20260517_006",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       1,
        transaction_type: "WITHDRAWAL",
        old_balance:      10000.00,
        new_balance:       7000.00,
        amount:            3000.00,
        status:           "UNCOMMITTED",          // ← CRASH left this here
        timestamp:        new Date("2026-05-17T10:00:00Z"),
        notes:            "CRASH: System failed mid-transaction — withdrawal never committed"
    },

    // ── Log 9: CRASH mid-deposit ─────────────────────────────
    {
        log_id:           9,
        transaction_id:   109,
        session_id:       "sess_20260517_006",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       3,
        transaction_type: "DEPOSIT",
        old_balance:      22000.00,
        new_balance:      24500.00,
        amount:            2500.00,
        status:           "UNCOMMITTED",          // ← CRASH left this here
        timestamp:        new Date("2026-05-17T10:00:05Z"),
        notes:            "CRASH: System failed — deposit never committed"
    },

    // ── Log 10: CRASH mid-transfer (partial) ─────────────────
    {
        log_id:           10,
        transaction_id:   110,
        session_id:       "sess_20260517_006",
        operation:        "UPDATE",
        table_name:       "Account",
        account_id:       7,
        transaction_type: "TRANSFER_OUT",
        old_balance:       3500.00,
        new_balance:       1000.00,
        amount:            2500.00,
        status:           "UNCOMMITTED",          // ← CRASH left this here
        timestamp:        new Date("2026-05-17T10:00:10Z"),
        notes:            "CRASH: Transfer OUT applied but COMMIT never reached — UNDO required"
    }

]);

print("  ✓ Inserted 3 UNCOMMITTED (crash-state) WAL log documents");


// ─────────────────────────────────────────
// Summary
// ─────────────────────────────────────────
print("\n" + "=".repeat(60));
print(" WAL Logs Inserted — Summary by Status:");
print("=".repeat(60));

const statuses = ["COMMITTED", "ROLLED_BACK", "UNCOMMITTED"];
statuses.forEach(s => {
    const count = db.wal_logs.countDocuments({ status: s });
    print(`  • ${s.padEnd(15)} : ${count} documents`);
});

print(`\n  Total WAL logs: ${db.wal_logs.countDocuments()}`);
print("\n  Run 03_recovery_logs.js next.");
print("=".repeat(60) + "\n");
