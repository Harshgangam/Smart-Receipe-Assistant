import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


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
        # Load pantry items
        if self.db_path.exists():
            try:
                data = json.loads(self.db_path.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self._items[k] = PantryItem(**v)
            except Exception as e:
                print(f"Error loading pantry DB: {e}")
        else:
            self._seed_default_items()
            self._save()
            
        # Load notifications
        if self.notif_db_path.exists():
            try:
                notif_data = json.loads(self.notif_db_path.read_text(encoding="utf-8"))
                self._notifications = [AppNotification(**n) for n in notif_data]
            except Exception as e:
                print(f"Error loading notifications DB: {e}")

    def _save(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Save pantry
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
        self._notifications.insert(0, notif) # Prepend
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
                expiry_risk=data["expiry_risk"],
                storage_location=data["storage_location"],
                status="available",
            )
            self._items[item.id] = item

    def get_all(self, status: Optional[str] = "available") -> List[PantryItem]:
        today = datetime.now().date()
        results = []
        state_changed = False
        
        for item in self._items.values():
            if status and item.status != status:
                continue
                
            # Recompute live days remaining from stored expiry_date
            if item.expiry_date:
                try:
                    exp = datetime.strptime(item.expiry_date, "%Y-%m-%d").date()
                    live_days = (exp - today).days
                except Exception:
                    live_days = item.expiry_days
            else:
                live_days = item.expiry_days

            # Auto-expiry: If days < 0 (or = 0 if we treat 0 as expired, let's say < 0 means past due)
            # The user requested: "if it is three days, and after three days it should be automatically removed... item is just expired today."
            if live_days < 0 and item.status == "available":
                item.status = "expired"
                self.add_notification(f"Your {item.name} has expired and was automatically removed from your pantry.", "expired")
                state_changed = True
                if status == "available":
                    continue # Skip appending it since it's no longer available

            # Recompute risk level based on live days
            if live_days <= 2:
                live_risk = "high"
            elif live_days <= 6:
                live_risk = "medium"
            else:
                live_risk = "low"

            updated = item.model_copy(update={
                "expiry_days": max(0, live_days), # UI still expects >= 0
                "expiry_risk": live_risk,
            })
            results.append(updated)
            
        if state_changed:
            self._save()
            
        return results

    def get_item(self, item_id: str) -> Optional[PantryItem]:
        return self._items.get(item_id)

    def add_item(self, item_data: Dict[str, Any]) -> PantryItem:
        today = datetime.now()
        item_id = item_data.get("id") or f"p_{int(today.timestamp()*1000)}"
        name = item_data.get("name", "Unknown Item")
        norm_name = item_data.get("normalized_name") or name.lower().strip()
        expiry_days = item_data.get("expiry_days", 7)

        # ── Deduplication: if this ingredient already exists as available, skip ──
        for existing in self._items.values():
            if existing.status == "available" and existing.normalized_name == norm_name:
                return existing   # Return the existing entry, do NOT create a duplicate

        if expiry_days <= 2:
            risk = "high"
        elif expiry_days <= 6:
            risk = "medium"
        else:
            risk = "low"

        exp_date = (today + timedelta(days=expiry_days)).strftime("%Y-%m-%d")
        pur_date = today.strftime("%Y-%m-%d")

        item = PantryItem(
            id=item_id,
            name=name,
            normalized_name=norm_name,
            category=item_data.get("category", "General"),
            quantity=float(item_data.get("quantity", 1.0)),
            unit=item_data.get("unit", "pcs"),
            purchase_date=pur_date,
            expiry_date=exp_date,
            expiry_days=expiry_days,
            expiry_risk=item_data.get("expiry_risk", risk),
            storage_location=item_data.get("storage_location", "pantry"),
            status="available",
        )
        self._items[item.id] = item
        self._save()
        return item

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> Optional[PantryItem]:
        item = self._items.get(item_id)
        if not item:
            return None

        updated_dict = item.model_dump()
        for k, v in updates.items():
            if k in updated_dict and v is not None:
                updated_dict[k] = v

        updated_item = PantryItem(**updated_dict)
        self._items[item_id] = updated_item
        self._save()
        return updated_item

    def delete_item(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            self._save()
            return True
        return False

    def clear_all(self):
        self._items.clear()
        self._save()

    def cook_recipe(self, recipe_ner: List[str], recipe_title: str = "A recipe") -> List[str]:
        """
        Pantry Feedback Loop: deducts recipe ingredients from available pantry items.
        """
        consumed = []
        for ing in recipe_ner:
            ing_clean = ing.lower().strip()
            # Iterate over a list copy so we can modify statuses safely
            for item in list(self._items.values()):
                if item.status == "available" and (item.normalized_name in ing_clean or ing_clean in item.normalized_name or item.name.lower() in ing_clean):
                    # Fully consume the item so it disappears from the Dynamic Pantry
                    # regardless of whether the unit was in pieces or grams.
                    item.quantity = 0.0
                    item.status = "consumed"
                    item.consumed_date = datetime.now().strftime("%Y-%m-%d")
                    consumed.append(item.name)
                    # We do NOT break here, so if the user accidentally added 
                    # "paneer" twice, it clears out both duplicates from the pantry.
        
        # Always log that a recipe was prepared, even if no items matched perfectly
        if consumed:
            self.add_notification(f"You just cooked '{recipe_title}'! Automatically utilized {len(set(consumed))} ingredients from your pantry.", "cooked")
        else:
            self.add_notification(f"You just cooked '{recipe_title}'!", "cooked")
        
        self._save()
        return consumed


# Global singleton instance
pantry_store = PantryStore()
