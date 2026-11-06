// ============================================================
// FILE: 01_setup_database.js
// PURPOSE: Create the MongoDB database and all collections
//          with schema validation for the WAL logging system
// PROJECT: ADBMS Final Project - Log-Based Recovery System
//
// HOW TO RUN:
//   Option A (mongosh CLI):
//     mongosh < 01_setup_database.js
//   Option B (mongosh interactive):
//     mongosh
//     > load("01_setup_database.js")
//   Option C (MongoDB Compass):
//     Open the "mongosh" tab at bottom → paste and run
// ============================================================

// ─────────────────────────────────────────
// STEP 1: Switch to (or create) the database
// MongoDB creates the DB automatically on first insert
// ─────────────────────────────────────────
use("bank_recovery_logs");

print("=".repeat(60));
print(" LOG-BASED RECOVERY SYSTEM — MongoDB Setup");
print(" ADBMS Final Project");
print("=".repeat(60));


// ─────────────────────────────────────────
// STEP 2: Drop existing collections (for clean re-run)
// ─────────────────────────────────────────
const existingCollections = db.getCollectionNames();

["wal_logs", "recovery_logs", "crash_log", "system_config"].forEach(name => {
    if (existingCollections.includes(name)) {
        db.getCollection(name).drop();
        print(`  Dropped existing collection: ${name}`);
    }
});


// ─────────────────────────────────────────
// STEP 3: Create 'wal_logs' collection with validation
//
// PURPOSE: Write-Ahead Log — every transaction writes here
//          BEFORE the PostgreSQL update is applied.
//          This is the core of the WAL logging concept.
//
// FIELDS:
//   log_id          — auto-sequential log number
//   transaction_id  — links to PostgreSQL Transaction_Record.transaction_id
//   session_id      — identifies the application session
//   operation       — UPDATE, INSERT, DELETE
//   table_name      — which PG table was affected
//   account_id      — which account (links to PG Account.account_id)
//   transaction_type— DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT
//   old_balance     — balance BEFORE the operation  ← used in UNDO
//   new_balance     — balance AFTER the operation   ← used in REDO
//   amount          — transaction amount
//   status          — UNCOMMITTED | COMMITTED | ROLLED_BACK
//   timestamp       — when the log was written
//   notes           — optional context
// ─────────────────────────────────────────
db.createCollection("wal_logs", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["log_id", "transaction_id", "operation", "account_id",
                       "old_balance", "new_balance", "status", "timestamp"],
            properties: {
                log_id: {
                    bsonType: "int",
                    description: "Sequential log identifier — required"
                },
                transaction_id: {
                    bsonType: "int",
                    description: "Links to PostgreSQL transaction_id — required"
                },
                session_id: {
                    bsonType: "string",
                    description: "Application session identifier"
                },
                operation: {
                    bsonType: "string",
                    enum: ["UPDATE", "INSERT", "DELETE"],
                    description: "Type of database operation — required"
                },
                table_name: {
                    bsonType: "string",
                    description: "PostgreSQL table affected"
                },
                account_id: {
                    bsonType: "int",
                    description: "Links to PostgreSQL Account.account_id — required"
                },
                transaction_type: {
                    bsonType: "string",
                    enum: ["DEPOSIT", "WITHDRAWAL", "TRANSFER_IN", "TRANSFER_OUT"],
                    description: "Nature of the financial transaction"
                },
                old_balance: {
                    bsonType: "double",
                    minimum: 0,
                    description: "Balance before operation — required for UNDO"
                },
                new_balance: {
                    bsonType: "double",
                    minimum: 0,
                    description: "Balance after operation — required for REDO"
                },
                amount: {
                    bsonType: "double",
                    description: "Transaction amount"
                },
                status: {
                    bsonType: "string",
                    enum: ["UNCOMMITTED", "COMMITTED", "ROLLED_BACK"],
                    description: "Transaction lifecycle status — required"
                },
                timestamp: {
                    bsonType: "date",
                    description: "When the log entry was created — required"
                },
                notes: {
                    bsonType: "string",
                    description: "Optional context or error message"
                }
            }
        }
    },
    validationLevel: "moderate",
    validationAction: "warn"
});

print("  ✓ Created collection: wal_logs");


// ─────────────────────────────────────────
// STEP 4: Create 'recovery_logs' collection
//
// PURPOSE: Records every action taken by the Recovery Manager.
//          Written AFTER undo/redo operations complete.
//          Serves as an audit trail of recovery actions.
// ─────────────────────────────────────────
db.createCollection("recovery_logs", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["recovery_id", "recovery_type", "transaction_id",
                       "account_id", "recovered_at"],
            properties: {
                recovery_id: {
                    bsonType: "int",
                    description: "Sequential recovery action ID"
                },
                recovery_type: {
                    bsonType: "string",
                    enum: ["UNDO", "REDO"],
                    description: "Whether this was an UNDO or REDO action"
                },
                transaction_id: {
                    bsonType: "int",
                    description: "The transaction that was undone/redone"
                },
                account_id: {
                    bsonType: "int",
                    description: "The account that was restored"
                },
                balance_before_recovery: {
                    bsonType: "double",
                    description: "Balance in PG before recovery applied"
                },
                balance_after_recovery: {
                    bsonType: "double",
                    description: "Balance in PG after recovery applied"
                },
                reason: {
                    bsonType: "string",
                    enum: ["CRASH_DETECTED", "MANUAL_ROLLBACK", "COMMIT_LOSS"],
                    description: "Why recovery was triggered"
                },
                recovered_at: {
                    bsonType: "date",
                    description: "Timestamp when recovery was applied"
                },
                recovery_session: {
                    bsonType: "string",
                    description: "Which recovery run this belongs to"
                }
            }
        }
    },
    validationLevel: "moderate",
    validationAction: "warn"
});

print("  ✓ Created collection: recovery_logs");


// ─────────────────────────────────────────
// STEP 5: Create 'crash_log' collection
//
// PURPOSE: Records each crash event detected by the system.
//          Stores which transactions were committed vs uncommitted
//          at the time of crash — used in the Analysis Phase.
// ─────────────────────────────────────────
db.createCollection("crash_log", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["crash_id", "crash_detected_at", "recovery_triggered"],
            properties: {
                crash_id: {
                    bsonType: "int",
                    description: "Sequential crash event ID"
                },
                crash_detected_at: {
                    bsonType: "date",
                    description: "When crash was detected"
                },
                uncommitted_transaction_ids: {
                    bsonType: "array",
                    description: "transaction_ids that were UNCOMMITTED at crash time"
                },
                committed_transaction_ids: {
                    bsonType: "array",
                    description: "transaction_ids that were COMMITTED at crash time"
                },
                recovery_triggered: {
                    bsonType: "bool",
                    description: "Whether recovery manager was run"
                },
                recovery_completed_at: {
                    bsonType: "date",
                    description: "When recovery completed"
                },
                recovery_summary: {
                    bsonType: "string",
                    description: "Human-readable summary of recovery actions"
                }
            }
        }
    },
    validationLevel: "moderate",
    validationAction: "warn"
});

print("  ✓ Created collection: crash_log");


// ─────────────────────────────────────────
// STEP 6: Create 'system_config' collection
//
// PURPOSE: Stores system-level metadata like the last
//          log_id counter and last recovery session info.
// ─────────────────────────────────────────
db.createCollection("system_config");

db.system_config.insertOne({
    config_key:        "log_counter",
    last_log_id:       0,
    last_recovery_id:  0,
    last_crash_id:     0,
    created_at:        new Date(),
    updated_at:        new Date(),
    description:       "Auto-increment counters for WAL log entries"
});

print("  ✓ Created collection: system_config");


// ─────────────────────────────────────────
// STEP 7: Create Indexes for performance
// ─────────────────────────────────────────

// wal_logs indexes
db.wal_logs.createIndex({ "transaction_id": 1 },          { name: "idx_wal_transaction_id" });
db.wal_logs.createIndex({ "status": 1 },                  { name: "idx_wal_status" });
db.wal_logs.createIndex({ "account_id": 1 },              { name: "idx_wal_account_id" });
db.wal_logs.createIndex({ "timestamp": -1 },              { name: "idx_wal_timestamp_desc" });
db.wal_logs.createIndex({ "status": 1, "timestamp": -1 }, { name: "idx_wal_status_time" });

// recovery_logs indexes
db.recovery_logs.createIndex({ "transaction_id": 1 },    { name: "idx_rec_transaction_id" });
db.recovery_logs.createIndex({ "recovery_type": 1 },     { name: "idx_rec_type" });
db.recovery_logs.createIndex({ "recovered_at": -1 },     { name: "idx_rec_timestamp" });

// crash_log indexes
db.crash_log.createIndex({ "crash_detected_at": -1 },    { name: "idx_crash_time" });

print("  ✓ Created indexes on all collections");


// ─────────────────────────────────────────
// STEP 8: Verify setup
// ─────────────────────────────────────────
print("\n" + "=".repeat(60));
print(" SETUP COMPLETE — Collections in bank_recovery_logs:");
print("=".repeat(60));

db.getCollectionNames().forEach(name => {
    const count = db.getCollection(name).countDocuments();
    print(`  • ${name.padEnd(20)} (${count} documents)`);
});

print("\n  Run 02_sample_wal_logs.js next to insert sample data.");
print("=".repeat(60) + "\n");
