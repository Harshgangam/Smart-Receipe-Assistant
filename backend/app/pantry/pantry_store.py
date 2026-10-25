import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.pantry.sqlite_pantry import sqlite_pantry


class PantryItem(BaseModel):
    id: str
    name: str
    normalized_name: str
    category: str = "General"
    quantity: float = 1.0
    unit: str = "pcs"
    purchase_date: Optional[str] = None
    expiry_date: Optional[str] = None
    expiry_days: int = 7
    expiry_risk: str = "low"  # "high", "medium", "low"
    storage_location: str = "pantry"  # "fridge", "pantry", "freezer"
    status: str = "available"  # "available", "consumed", "expired"
    consumed_date: Optional[str] = None
    detection_source: Optional[str] = "manual"
    confidence: Optional[float] = 1.0
    user_confirmed: Optional[int] = 1


class AppNotification(BaseModel):
    id: str
    message: str
    type: str  # e.g., "expired", "cooked"
    read: bool = False
    timestamp: str


class PantryStore:
    def __init__(self):
        from backend.app.config import settings
        self.db_path = settings.DATA_DIR / "pantry_db.json"
        self.notif_db_path = settings.DATA_DIR / "notifications_db.json"
        self._items: Dict[str, PantryItem] = {}
        self._notifications: List[AppNotification] = []
        self._load_from_disk()

    def _load_from_disk(self):
        # 1. Load notifications
        if self.notif_db_path.exists():
            try:
                notif_data = json.loads(self.notif_db_path.read_text(encoding="utf-8"))
                self._notifications = [AppNotification(**n) for n in notif_data]
            except Exception as e:
                print(f"Error loading notifications DB: {e}")

        # 2. Sync from SQLite Pantry Store as primary source of truth
        sqlite_items = sqlite_pantry.get_all(status=None)
        if sqlite_items:
            for item_dict in sqlite_items:
                self._items[item_dict["id"]] = PantryItem(**item_dict)
        elif self.db_path.exists():
            try:
                data = json.loads(self.db_path.read_text(encoding="utf-8"))
                for k, v in data.items():
                    item = PantryItem(**v)
                    self._items[k] = item
                    sqlite_pantry.add_or_upsert_item(item.model_dump())
            except Exception as e:
                print(f"Error loading pantry DB: {e}")
        else:
            self._seed_default_items()
            self._save()

    def _save(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Save JSON cache
        data = {k: v.model_dump() for k, v in self._items.items()}
        self.db_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        # Save notifications
        notif_data = [n.model_dump() for n in self._notifications]
        self.notif_db_path.write_text(json.dumps(notif_data, indent=2), encoding="utf-8")

    def add_notification(self, message: str, type: str):
        notif = AppNotification(
            id=f"n_{int(datetime.now().timestamp()*1000)}",
            message=message,
            type=type,
            read=False,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self._notifications.insert(0, notif)
        self._save()

    def get_notifications(self) -> List[AppNotification]:
        return self._notifications

    def mark_notifications_read(self):
        for n in self._notifications:
            n.read = True
        self._save()

    def _seed_default_items(self):
        today = datetime.now()
        seed_data = []
        for data in seed_data:
            days = data["expiry_days"]
            exp_date = (today + timedelta(days=days)).strftime("%Y-%m-%d")
            pur_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
            norm_name = data["name"].lower().replace("fresh ", "").replace("cheddar ", "").replace("breast", "").strip()

            item = PantryItem(
                id=data["id"],
                name=data["name"],
                normalized_name=norm_name,
                category=data["category"],
                quantity=data["quantity"],
                unit=data["unit"],
                purchase_date=pur_date,
                expiry_date=exp_date,
                expiry_days=days,
                expiry_risk="high" if days <= 2 else ("medium" if days <= 6 else "low"),
                storage_location=data["storage_location"],
                status="available",
                detection_source="seed",
            )
            self._items[item.id] = item
            sqlite_pantry.add_or_upsert_item(item.model_dump())

    def get_all(self, status: Optional[str] = "available") -> List[PantryItem]:
        today = datetime.now().date()
        results = []
        state_changed = False

        sqlite_rows = sqlite_pantry.get_all(status=status)
        for row in sqlite_rows:
            item = PantryItem(**row)
            # Auto-expiry notification
            if item.expiry_days <= 0 and item.status == "available":
                item.status = "expired"
                sqlite_pantry.update_item(item.id, {"status": "expired"})
                self.add_notification(f"Your {item.name} has expired and was marked expired.", "expired")
                state_changed = True
                if status == "available":
                    continue
            results.append(item)
            self._items[item.id] = item

        if state_changed:
            self._save()

        return results

    def get_item(self, item_id: str) -> Optional[PantryItem]:
        row = sqlite_pantry.get_item(item_id)
        return PantryItem(**row) if row else None

    def add_item(self, item_data: Dict[str, Any]) -> PantryItem:
        row = sqlite_pantry.add_or_upsert_item(item_data)
        item = PantryItem(**row)
        self._items[item.id] = item
        self._save()
        return item

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> Optional[PantryItem]:
        row = sqlite_pantry.update_item(item_id, updates)
        if not row:
            return None
        item = PantryItem(**row)
        self._items[item_id] = item
        self._save()
        return item

    def delete_item(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
        success = sqlite_pantry.delete_item(item_id)
        self._save()
        return success

    def clear_all(self):
        self._items.clear()
        sqlite_pantry.clear_all()
        self._save()

    def cook_recipe(self, recipe_ner: List[str], recipe_title: str = "A recipe") -> List[str]:
        consumed = sqlite_pantry.cook_recipe(recipe_ner, recipe_title)
        # Refresh in-memory cache
        self.get_all(status=None)

        if consumed:
            self.add_notification(f"You just cooked '{recipe_title}'! Utilized {len(set(consumed))} ingredients from your pantry.", "cooked")
        else:
            self.add_notification(f"You just cooked '{recipe_title}'!", "cooked")

        self._save()
        return consumed


pantry_store = PantryStore()
