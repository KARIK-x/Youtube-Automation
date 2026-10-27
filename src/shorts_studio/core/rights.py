"""Rights registry and gate."""
import sqlite3, json, time, hashlib
from pathlib import Path

RIGHTS_STATES = {"UNKNOWN","REVIEW_REQUIRED","AUTHORIZED","LICENSED","PUBLIC_DOMAIN_VERIFIED","REJECTED"}

class RightsRegistry:
    def __init__(self, db):
        self.db = db
        self.db.conn.execute("""
        CREATE TABLE IF NOT EXISTS rights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_path TEXT,
            source_url TEXT,
            creator TEXT,
            acquisition_method TEXT,
            license_type TEXT DEFAULT 'UNKNOWN',
            evidence TEXT,
            allowed_uses TEXT,
            attribution TEXT,
            commercial_restrictions TEXT,
            modification_restrictions TEXT,
            expiry REAL,
            review_status TEXT DEFAULT 'UNKNOWN',
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL DEFAULT (strftime('%s','now'))
        )""")
        self.db.conn.commit()

    def register(self, asset_path=None, source_url=None, creator=None, acquisition_method=None,
                license_type="UNKNOWN", evidence=None, allowed_uses=None, attribution=None,
                commercial_restrictions=None, modification_restrictions=None, expiry=None,
                review_status="UNKNOWN"):
        if review_status not in RIGHTS_STATES:
            review_status = "UNKNOWN"
        cur = self.db.conn.execute("""
            INSERT INTO rights(asset_path,source_url,creator,acquisition_method,license_type,evidence,
            allowed_uses,attribution,commercial_restrictions,modification_restrictions,expiry,review_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (asset_path, source_url, creator, acquisition_method, license_type,
             json.dumps(evidence) if evidence else None,
             json.dumps(allowed_uses) if allowed_uses else None,
             attribution, commercial_restrictions, modification_restrictions, expiry, review_status))
        self.db.conn.commit()
        return cur.lastrowid

    def get(self, rights_id):
        r = self.db.conn.execute("SELECT * FROM rights WHERE id=?", (rights_id,)).fetchone()
        return dict(r) if r else None

    def update_status(self, rights_id, status, evidence=None):
        if status not in RIGHTS_STATES:
            raise ValueError(f"invalid rights state {status}")
        self.db.conn.execute("UPDATE rights SET review_status=?, evidence=COALESCE(?,evidence), updated_at=? WHERE id=?",
                             (status, json.dumps(evidence) if evidence else None, time.time(), rights_id))
        self.db.conn.commit()

    def gate(self, rights_id):
        """Return (allowed: bool, reason: str). Hard gate: only AUTHORIZED/LICENSED/PUBLIC_DOMAIN_VERIFIED pass."""
        r = self.get(rights_id)
        if r is None:
            return False, "rights record missing"
        st = r["review_status"]
        if st in ("AUTHORIZED","LICENSED","PUBLIC_DOMAIN_VERIFIED"):
            return True, f"rights state {st}"
        return False, f"rights not cleared: {st}"

    def gate_by_source(self, source_path):
        rows = self.db.conn.execute("SELECT * FROM rights WHERE asset_path=? OR source_url=?", (source_path, source_path)).fetchall()
        if not rows:
            return False, "no rights record for source"
        # if any cleared, allow
        for r in rows:
            if r["review_status"] in ("AUTHORIZED","LICENSED","PUBLIC_DOMAIN_VERIFIED"):
                return True, f"rights state {r['review_status']}"
        return False, f"rights not cleared: {rows[0]['review_status']}"
