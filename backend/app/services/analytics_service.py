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
        
        # Real-time Factual Utilization Rate (consumed items / total items ever tracked)
        utilization_rate = (consumed_count / total_items_tracked * 100.0) if total_items_tracked > 0 else 0.0
        
        # Recipes prepared is the actual number of 'cooked' notifications logged
        notifications = pantry_store.get_notifications()
        recipes_prepared = sum(1 for n in notifications if n.type == "cooked")

        trend_data = []
        today = datetime.datetime.now()
        
        # Calculate daily usage based on actual records
        daily_rescues = {}
        for i in range(7):
            d = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            daily_rescues[d] = 0
            
        for item in consumed_items:
            d = getattr(item, "consumed_date", None)
            if d:
                d = str(d).split()[0]
            elif getattr(item, "id", None) and str(item.id).startswith("p_"):
                try:
                    ts = int(str(item.id).split("_")[1]) / 1000.0
                    d = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                except Exception:
                    d = None
            if d and d in daily_rescues:
                daily_rescues[d] += 1

        for notif in notifications:
            if notif.type == "cooked" and notif.timestamp:
                try:
                    nd = str(notif.timestamp).split()[0]
                    if nd in daily_rescues:
                        daily_rescues[nd] += 1
                except Exception:
                    pass

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

        if consumed_count > 0:
            status_msg = f"Pantry tracking active: {consumed_count} item{'s' if consumed_count != 1 else ''} consumed across {recipes_prepared} home-prepared meal{'s' if recipes_prepared != 1 else ''}."
        elif recipes_prepared > 0:
            status_msg = f"Pantry tracking active: {recipes_prepared} home meal{'s' if recipes_prepared != 1 else ''} prepared. {len(available_items)} active ingredients ready in pantry."
        else:
            status_msg = f"Your pantry has {len(available_items)} active ingredients on hand. Cook recipes or log used items to track pantry utilization."

        return {
            "high_risk_rescued_count": consumed_count,
            "pantry_utilization_rate": round(utilization_rate, 1),
            "estimated_food_waste_avoided_kg": 0.0,
            "recipes_prepared_count": recipes_prepared,
            "current_high_risk_pantry_count": len(high_risk_items),
            "active_pantry_count": len(available_items),
            "total_items_tracked": total_items_tracked,
            "sustainability_trend": trend_data,
            "status_summary": status_msg
        }
