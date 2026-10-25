"""
backend/app/pantry/sqlite_pantry.py

SQLite-backed Pantry Management System:
Provides transactional CRUD operations, UPSERT logic, duplicate prevention,
confidence tracking, detection source provenance, and auto-migration from JSON.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.app.config import settings

logger = logging.getLogger(__name__)


class SQLitePantryStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (settings.DATA_DIR / "pantry.sqlite")
        self._ensure_db()
        self._migrate_from_json_if_needed()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self):
        """Initializes the SQLite schema with safe indexing and UPSERT constraints."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pantry_items (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    category TEXT DEFAULT 'General',
                    quantity REAL DEFAULT 1.0,
                    unit TEXT DEFAULT 'pcs',
                    purchase_date TEXT,
                    expiry_date TEXT,
                    expiry_days INTEGER DEFAULT 7,
                    expiry_risk TEXT DEFAULT 'low',
                    storage_location TEXT DEFAULT 'pantry',
                    status TEXT DEFAULT 'available',
                    consumed_date TEXT,
                    detection_source TEXT DEFAULT 'manual',
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT,
                    updated_at TEXT,
                    user_confirmed INTEGER DEFAULT 1
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pantry_status_norm 
                ON pantry_items (status, normalized_name);
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vision_intake_logs (
                    id TEXT PRIMARY KEY,
                    raw_filename TEXT,
                    timestamp TEXT,
                    items_detected_count INTEGER,
                    items_confirmed_count INTEGER,
                    status TEXT
                );
            """)
            conn.commit()

    def _migrate_from_json_if_needed(self):
        """Seamlessly migrates existing legacy pantry_db.json into SQLite on first startup."""
        json_path = settings.DATA_DIR / "pantry_db.json"
        if not json_path.exists():
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM pantry_items")
            row = cursor.fetchone()
            if row and row["count"] > 0:
                return  # Already populated

            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for k, v in data.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO pantry_items (
                            id, name, normalized_name, category, quantity, unit,
                            purchase_date, expiry_date, expiry_days, expiry_risk,
                            storage_location, status, consumed_date, detection_source,
                            confidence, created_at, updated_at, user_confirmed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        v.get("id", k),
                        v.get("name", "Unknown"),
                        v.get("normalized_name", v.get("name", "").lower()),
                        v.get("category", "General"),
                        float(v.get("quantity", 1.0)),
                        v.get("unit", "pcs"),
                        v.get("purchase_date"),
                        v.get("expiry_date"),
                        int(v.get("expiry_days", 7)),
                        v.get("expiry_risk", "low"),
                        v.get("storage_location", "pantry"),
                        v.get("status", "available"),
                        v.get("consumed_date"),
                        "legacy_json_import",
                        1.0,
                        now_str,
                        now_str,
                        1
                    ))
                conn.commit()
                logger.info(f"Successfully migrated {len(data)} items from pantry_db.json to pantry.sqlite.")
            except Exception as e:
                logger.warning(f"Notice: legacy json migration skipped ({e})")

    def get_all(self, status: Optional[str] = "available") -> List[Dict[str, Any]]:
        """Retrieves items filtered by status, updating dynamic expiry risks."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM pantry_items WHERE status = ? ORDER BY created_at DESC",
                    (status,)
                )
            else:
                cursor.execute("SELECT * FROM pantry_items ORDER BY created_at DESC")
            
            rows = cursor.fetchall()
            results = []
            today = datetime.now().date()

            for r in rows:
                item = dict(r)
                # Recalculate dynamic days remaining & risk if expiry_date is set
                if item.get("expiry_date"):
                    try:
                        exp = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
                        days_left = (exp - today).days
                        item["expiry_days"] = max(0, days_left)
                        if days_left <= 2:
                            item["expiry_risk"] = "high"
                        elif days_left <= 6:
                            item["expiry_risk"] = "medium"
                        else:
                            item["expiry_risk"] = "low"
                    except Exception:
                        pass
                results.append(item)
            return results

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pantry_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_or_upsert_item(self, item_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds or updates an ingredient with UPSERT duplicate-prevention logic.
        If an available item with the same normalized name exists, merges quantity.
        """
        now = datetime.now()
        name = item_dict.get("name", "").strip()
        from backend.app.services.ingredient_normalizer import ingredient_normalizer
        canonical_name, _, _ = ingredient_normalizer.normalize(name)
        normalized = item_dict.get("normalized_name") or canonical_name

        days = int(item_dict.get("expiry_days", 7))
        exp_date = item_dict.get("expiry_date") or (now + timedelta(days=days)).strftime("%Y-%m-%d")
        pur_date = item_dict.get("purchase_date") or now.strftime("%Y-%m-%d")
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        qty = float(item_dict.get("quantity", 1.0))
        unit = item_dict.get("unit", "pcs")
        category = item_dict.get("category", "General")
        source = item_dict.get("detection_source", "manual")
        conf = float(item_dict.get("confidence", 1.0))
        confirmed = 1 if item_dict.get("user_confirmed", True) else 0

        # Calculate initial risk
        risk = "high" if days <= 2 else ("medium" if days <= 6 else "low")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check for existing active item
            cursor.execute(
                "SELECT * FROM pantry_items WHERE normalized_name = ? AND status = 'available'",
                (normalized,)
            )
            existing = cursor.fetchone()

            if existing:
                item_id = existing["id"]
                new_qty = existing["quantity"] + qty
                # Update existing record
                cursor.execute("""
                    UPDATE pantry_items SET
                        quantity = ?,
                        expiry_date = ?,
                        expiry_days = ?,
                        expiry_risk = ?,
                        detection_source = ?,
                        confidence = ?,
                        updated_at = ?,
                        user_confirmed = ?
                    WHERE id = ?
                """, (new_qty, exp_date, days, risk, source, conf, now_str, confirmed, item_id))
            else:
                item_id = item_dict.get("id") or f"p_{int(now.timestamp() * 1000)}"
                cursor.execute("""
                    INSERT INTO pantry_items (
                        id, name, normalized_name, category, quantity, unit,
                        purchase_date, expiry_date, expiry_days, expiry_risk,
                        storage_location, status, detection_source, confidence,
                        created_at, updated_at, user_confirmed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available', ?, ?, ?, ?, ?)
                """, (
                    item_id, name, normalized, category, qty, unit,
                    pur_date, exp_date, days, risk,
                    item_dict.get("storage_location", "pantry"),
                    source, conf, now_str, now_str, confirmed
                ))
            conn.commit()

        return self.get_item(item_id) # type: ignore

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            for k, v in updates.items():
                if k != "id":
                    fields.append(f"{k} = ?")
                    values.append(v)
            if not fields:
                return self.get_item(item_id)

            fields.append("updated_at = ?")
            values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            values.append(item_id)

            sql = f"UPDATE pantry_items SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(sql, tuple(values))
            conn.commit()

        return self.get_item(item_id)

    def delete_item(self, item_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pantry_items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pantry_items")
            conn.commit()

    def cook_recipe(self, recipe_ner: List[str], recipe_title: str) -> List[str]:
        """
        Deducts consumed ingredients from available inventory.
        """
        consumed = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for ing in recipe_ner:
                norm = ing.lower().strip()
                cursor.execute("""
                    SELECT id, quantity, name FROM pantry_items 
                    WHERE status = 'available' AND (normalized_name = ? OR normalized_name LIKE ?)
                    LIMIT 1
                """, (norm, f"%{norm}%"))
                row = cursor.fetchone()
                if row:
                    curr_qty = row["quantity"]
                    if curr_qty <= 1.0:
                        cursor.execute("""
                            UPDATE pantry_items SET 
                                status = 'consumed',
                                consumed_date = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (now_str, now_str, row["id"]))
                    else:
                        cursor.execute("""
                            UPDATE pantry_items SET 
                                quantity = quantity - 1.0,
                                updated_at = ?
                            WHERE id = ?
                        """, (now_str, row["id"]))
                    consumed.append(row["name"])
            conn.commit()

        return consumed


sqlite_pantry = SQLitePantryStore()
