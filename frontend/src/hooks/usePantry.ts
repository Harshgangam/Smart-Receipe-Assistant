import { useCallback, useState } from 'react';
import { addPantryItem } from '../services/api';
import { isSameFood } from '../utils/foodNormalizer';

export function usePantry(initialIngredients: string[] = []) {
  const [ingredients, setIngredients] = useState<string[]>(initialIngredients);

  /**
   * Adds ingredient to local state AND calls the backend pantry API
   * when expiryDays is provided (set via Freshness Buttons).
   * This ensures the Dynamic Pantry Intelligence tab gets a live countdown.
   * Recognizes ingredients semantically (e.g. "4 potatoes" and "potatoes" are the same).
   */
  const addIngredient = useCallback((rawItem: string, expiryDays?: number): boolean => {
    if (!rawItem || !rawItem.trim()) return false;

    // Support comma-separated pastes e.g. "tomato, garlic, pasta"
    const items = rawItem
      .split(',')
      .map((i) => i.trim().toLowerCase())
      .filter((i) => i.length > 0);

    let addedCount = 0;
    setIngredients((prev) => {
      const next = [...prev];
      for (const item of items) {
        const alreadyExists = next.some((existing) => isSameFood(existing, item));
        if (!alreadyExists) {
          next.push(item);
          addedCount++;

          // Persist to backend pantry store so Pantry Intelligence
          // shows the live countdown for this ingredient
          if (expiryDays !== undefined) {
            addPantryItem({
              name: item,
              category: 'General',
              quantity: 1,
              unit: 'pcs',
              expiry_days: expiryDays,
            }).catch(() => {
              // Silently ignore if backend call fails —
              // local state is still updated
            });
          }
        }
      }
      return next;
    });

    return addedCount > 0;
  }, []);

  const removeIngredient = useCallback((itemToRemove: string) => {
    setIngredients((prev) =>
      prev.filter((i) => !isSameFood(i, itemToRemove) && i.toLowerCase() !== itemToRemove.toLowerCase())
    );
  }, []);

  const clearPantry = useCallback(() => {
    setIngredients([]);
  }, []);

  const addMultiple = useCallback((newItems: string[]) => {
    setIngredients((prev) => {
      const next = [...prev];
      for (const item of newItems) {
        const norm = item.trim().toLowerCase();
        if (norm && !next.some((existing) => isSameFood(existing, norm))) {
          next.push(norm);
        }
      }
      return next;
    });
  }, []);

  const setPantry = useCallback((newItems: string[]) => {
    setIngredients(newItems.map((i) => i.trim().toLowerCase()).filter(Boolean));
  }, []);

  return {
    ingredients,
    addIngredient,
    removeIngredient,
    clearPantry,
    addMultiple,
    setPantry,
  };
}
