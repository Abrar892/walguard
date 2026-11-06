// ============================================================
// FILE: 04_queries.js
// PURPOSE: All useful mongosh queries for exploring, filtering,
//          and demonstrating the WAL logging system
//
// HOW TO RUN:
//   Run individual sections in mongosh or MongoDB Compass Shell
//   Each section is clearly labeled — run them one at a time
//   during your demo or viva
// ============================================================

use("bank_recovery_logs");

print("=".repeat(60));
print(" MongoDB Query Demonstrations");
print(" Log-Based Recovery System — ADBMS Project");
print("=".repeat(60));


// ─────────────────────────────────────────
// QUERY 1: View ALL WAL Logs (sorted newest first)
// ─────────────────────────────────────────
print("\n── QUERY 1: All WAL Logs ──");
db.wal_logs.find(
    {},
    { _id: 0, log_id: 1, transaction_id: 1, account_id: 1,
      transaction_type: 1, amount: 1, old_balance: 1, new_balance: 1,
      status: 1, timestamp: 1 }
).sort({ timestamp: -1 }).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 2: Find UNCOMMITTED logs (crash detection query)
// This is the first thing Recovery Manager runs —
// the Analysis Phase
// ─────────────────────────────────────────
print("\n── QUERY 2: UNCOMMITTED Logs (Recovery Targets) ──");
db.wal_logs.find(
    { status: "UNCOMMITTED" },
    { _id: 0, log_id: 1, transaction_id: 1, account_id: 1,
      old_balance: 1, new_balance: 1, status: 1, notes: 1 }
).sort({ timestamp: 1 }).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 3: Find COMMITTED logs (redo candidates)
// ─────────────────────────────────────────
print("\n── QUERY 3: COMMITTED Logs (Redo Candidates) ──");
db.wal_logs.find(
    { status: "COMMITTED" },
    { _id: 0, log_id: 1, transaction_id: 1, account_id: 1,
      transaction_type: 1, old_balance: 1, new_balance: 1, timestamp: 1 }
).sort({ timestamp: 1 }).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 4: Filter by account_id (e.g., account 1)
// ─────────────────────────────────────────
print("\n── QUERY 4: WAL Logs for account_id = 1 ──");
db.wal_logs.find(
    { account_id: 1 },
    { _id: 0, log_id: 1, transaction_id: 1, transaction_type: 1,
      amount: 1, old_balance: 1, new_balance: 1, status: 1, timestamp: 1 }
).sort({ timestamp: 1 }).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 5: Filter by transaction_type (WITHDRAWALS only)
// ─────────────────────────────────────────
print("\n── QUERY 5: All WITHDRAWAL Logs ──");
db.wal_logs.find(
    { transaction_type: "WITHDRAWAL" },
    { _id: 0, log_id: 1, transaction_id: 1, account_id: 1,
      amount: 1, old_balance: 1, new_balance: 1, status: 1 }
).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 6: Count logs by status (aggregation)
// Shows the overall system state at a glance
// ─────────────────────────────────────────
print("\n── QUERY 6: Log Count by Status (Aggregation) ──");
db.wal_logs.aggregate([
    {
        $group: {
            _id:   "$status",
            count: { $sum: 1 },
            total_amount: { $sum: "$amount" }
        }
    },
    { $sort: { _id: 1 } }
]).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 7: Count logs by transaction_type
// ─────────────────────────────────────────
print("\n── QUERY 7: Log Count by Transaction Type ──");
db.wal_logs.aggregate([
    {
        $group: {
            _id:          "$transaction_type",
            count:        { $sum: 1 },
            total_amount: { $sum: "$amount" },
            avg_amount:   { $avg: "$amount" }
        }
    },
    { $sort: { _id: 1 } }
]).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 8: Show what UNDO operation needs to do
// Pairs each UNCOMMITTED log with the balance to restore
// ─────────────────────────────────────────
print("\n── QUERY 8: UNDO Plan — What Recovery Manager Will Restore ──");
db.wal_logs.aggregate([
    { $match: { status: "UNCOMMITTED" } },
    {
        $project: {
            _id:             0,
            log_id:          1,
            transaction_id:  1,
            account_id:      1,
            transaction_type: 1,
            current_balance:  "$new_balance",
            restore_to:       "$old_balance",
            difference: {
                $subtract: ["$new_balance", "$old_balance"]
            },
            undo_action: {
                $concat: [
                    "UPDATE Account SET balance = ",
                    { $toString: "$old_balance" },
                    " WHERE account_id = ",
                    { $toString: "$account_id" }
                ]
            }
        }
    },
    { $sort: { timestamp: -1 } }   // Undo newest first
]).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 9: Show REDO plan for COMMITTED logs
// ─────────────────────────────────────────
print("\n── QUERY 9: REDO Plan — Committed Transactions to Re-apply ──");
db.wal_logs.aggregate([
    { $match: { status: "COMMITTED" } },
    {
        $project: {
            _id:            0,
            log_id:         1,
            transaction_id: 1,
            account_id:     1,
            apply_balance:  "$new_balance",
            redo_action: {
                $concat: [
                    "UPDATE Account SET balance = ",
                    { $toString: "$new_balance" },
                    " WHERE account_id = ",
                    { $toString: "$account_id" }
                ]
            }
        }
    }
]).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 10: View ALL recovery_logs
// ─────────────────────────────────────────
print("\n── QUERY 10: All Recovery Log Entries ──");
db.recovery_logs.find(
    {},
    { _id: 0 }
).sort({ recovered_at: 1 }).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 11: View crash_log (crash event details)
// ─────────────────────────────────────────
print("\n── QUERY 11: Crash Log Events ──");
db.crash_log.find({}, { _id: 0 }).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 12: Recovery summary — group UNDO vs REDO
// ─────────────────────────────────────────
print("\n── QUERY 12: Recovery Summary by Type ──");
db.recovery_logs.aggregate([
    {
        $group: {
            _id:             "$recovery_type",
            count:           { $sum: 1 },
            accounts_fixed:  { $addToSet: "$account_id" }
        }
    }
]).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 13: Time-range query — logs from last hour
// ─────────────────────────────────────────
print("\n── QUERY 13: WAL Logs from Last 24 Hours ──");
const since = new Date(Date.now() - 24 * 60 * 60 * 1000);
db.wal_logs.find(
    { timestamp: { $gte: since } },
    { _id: 0, log_id: 1, transaction_id: 1, account_id: 1,
      status: 1, timestamp: 1 }
).sort({ timestamp: -1 }).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 14: Find sessions with UNCOMMITTED logs
// Groups by session to find which sessions crashed
// ─────────────────────────────────────────
print("\n── QUERY 14: Crashed Sessions (sessions with UNCOMMITTED logs) ──");
db.wal_logs.aggregate([
    { $match: { status: "UNCOMMITTED" } },
    {
        $group: {
            _id:                    "$session_id",
            uncommitted_count:      { $sum: 1 },
            affected_transactions:  { $push: "$transaction_id" },
            affected_accounts:      { $addToSet: "$account_id" }
        }
    }
]).forEach(doc => printjson(doc));


// ─────────────────────────────────────────
// QUERY 15: WAL completeness check
// Verifies every log has all required fields
// ─────────────────────────────────────────
print("\n── QUERY 15: Validate Log Completeness ──");
const totalLogs = db.wal_logs.countDocuments();
const completeLogs = db.wal_logs.countDocuments({
    log_id:           { $exists: true },
    transaction_id:   { $exists: true },
    account_id:       { $exists: true },
    old_balance:      { $exists: true },
    new_balance:      { $exists: true },
    status:           { $exists: true },
    timestamp:        { $exists: true }
});

print(`  Total logs     : ${totalLogs}`);
print(`  Complete logs  : ${completeLogs}`);
print(`  Incomplete logs: ${totalLogs - completeLogs}`);
print(`  Completeness   : ${((completeLogs / totalLogs) * 100).toFixed(1)}%`);

print("\n" + "=".repeat(60));
print(" All queries complete.");
print("=".repeat(60) + "\n");
