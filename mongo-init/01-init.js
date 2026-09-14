db = db.getSiblingDB("alcancepro");

db.createCollection("users");
db.createCollection("expedientes");
db.createCollection("documents");
db.createCollection("analysis_jobs");
db.createCollection("scope_items");
db.createCollection("deliverables");
db.createCollection("audit_logs");

db.users.createIndex({ email: 1 }, { unique: true });
db.expedientes.createIndex({ code: 1 }, { unique: true });
db.expedientes.createIndex({ owner_id: 1, created_at: -1 });
db.documents.createIndex({ expediente_id: 1, created_at: -1 });
db.analysis_jobs.createIndex({ expediente_id: 1, created_at: -1 });
db.scope_items.createIndex({ expediente_id: 1, sort_order: 1 });
db.deliverables.createIndex({ expediente_id: 1, sort_order: 1 });
