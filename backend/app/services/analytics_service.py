from typing import Dict, Any, List
import datetime
from backend.app.pantry.pantry_store import pantry_store


class SustainabilityAnalyticsService:
    @staticmethod
    def get_sustainability_metrics() -> Dict[str, Any]:
        pantry_items = pantry_store.get_all(status=None)
        available_items = [item for item in pantry_items if item.status == "available"]
        consumed_items = [item for item in pantry_items if item.status == "consumed"]
        high_risk_items = [item for item in available_items if item.expiry_risk == "high"]

        total_items_tracked = len(pantry_items)
        consumed_count = len(consumed_items)
        
        # Real-time Utilization Rate
        utilization_rate = (consumed_count / total_items_tracked * 100.0) if total_items_tracked > 0 else 0.0

        # Real-time items rescued
        # We assume each consumed item was "rescued" from being thrown away
        rescued_total = consumed_count
        waste_avoided_kg = round(rescued_total * 0.35, 2)  # Avg 0.35kg per item
        
        # Recipes prepared is the number of 'cooked' notifications
        notifications = pantry_store.get_notifications()
        recipes_prepared = sum(1 for n in notifications if n.type == "cooked")

        trend_data = []
        today = datetime.datetime.now()
        
        # Calculate daily usage based on the actual calendar days
        daily_rescues = {}
        for i in range(7):
            d = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            daily_rescues[d] = 0
            
        for item in consumed_items:
            d = getattr(item, "consumed_date", None)
            if not d and getattr(item, "id", None) and str(item.id).startswith("p_"):
                try:
                    ts = int(str(item.id).split("_")[1]) / 1000.0
                    d = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                except Exception:
                    d = None
            if d and d in daily_rescues:
                daily_rescues[d] += 1

        # Build 7-day trend array (from oldest to today)
        for i in range(6, -1, -1):
            date_obj = today - datetime.timedelta(days=i)
            d_str = date_obj.strftime("%Y-%m-%d")
            day_name = date_obj.strftime("%a")
            
            items = daily_rescues.get(d_str, 0)
            pct = round((items / total_items_tracked * 100.0), 1) if total_items_tracked > 0 else 0
            
            trend_data.append({
                "day": day_name,
                "rescued_items": items,
                "utilization_pct": pct
            })

        if rescued_total == 0:
            status_msg = "Your pantry utilization journey starts here. Cook recipes to utilize items and track your impact!"
        else:
            status_msg = f"Great job! You have utilized {rescued_total} ingredients."

        return {
            "high_risk_rescued_count": rescued_total,
            "pantry_utilization_rate": round(utilization_rate, 1),
            "estimated_food_waste_avoided_kg": waste_avoided_kg,
            "recipes_prepared_count": recipes_prepared,
            "current_high_risk_pantry_count": len(high_risk_items),
            "active_pantry_count": len(available_items),
            "sustainability_trend": trend_data,
            "status_summary": status_msg
        }
