import { useCallback, useEffect, useState } from 'react';
import { addPantryItem, clearAllPantryItems, deletePantryItemByName, fetchPantryItems } from '../services/api';

export function usePantry(initialIngredients: string[] = []) {
  const [ingredients, setIngredients] = useState<string[]>(initialIngredients);

  const refreshPantry = useCallback(async (): Promise<string[]> => {
    try {
      const items = await fetchPantryItems();
      if (items && Array.isArray(items)) {
        const names = items.map((i) => i.name.toLowerCase().trim()).filter(Boolean);
        const unique = Array.from(new Set(names));
        setIngredients(unique);
        return unique;
      }
    } catch (err) {
      console.error('Failed to load initial pantry items:', err);
    }
    return [];
  }, []);

  // 1. Initial sync: load existing items from Pantry Intelligence into Kitchen Pantry
  useEffect(() => {
    refreshPantry();
  }, [refreshPantry]);

  // 2. Add ingredient: updates Kitchen Pantry immediately and persists to SQLite backend
  const addIngredient = useCallback((rawItem: string, expiryDays: number = 7): boolean => {
    if (!rawItem || !rawItem.trim()) return false;
    const items = rawItem
      .split(',')
      .map((i) => i.trim().toLowerCase())
      .filter((i) => i.length > 0);
    const itemsToAdd: string[] = [];
    setIngredients((prev) => {
      const existing = new Set(prev.map((i) => i.toLowerCase()));
      const next = [...prev];
      for (const item of items) {
        if (!existing.has(item)) {
          existing.add(item);
          next.push(item);
          itemsToAdd.push(item);
        }
      }
      return next;
    });

    // Save to backend pantry so it appears in Pantry Intelligence
    itemsToAdd.forEach((item) => {
      addPantryItem({
        name: item,
        category: 'General',
        quantity: 1,
        unit: 'pcs',
        expiry_days: expiryDays || 7,
      }).catch((err) => {
        console.error(`Failed to save ${item} to backend pantry:`, err);
      });
    });

    return itemsToAdd.length > 0;
  }, []);

  // 3. Remove ingredient: removes from local UI state and deletes from SQLite backend
  const removeIngredient = useCallback((itemToRemove: string) => {
    const cleanName = itemToRemove.trim().toLowerCase();
    setIngredients((prev) =>
      prev.filter((i) => i.toLowerCase() !== cleanName)
    );
    deletePantryItemByName(cleanName);
  }, []);

  // 4. Clear all ingredients: clears both local state and backend database
  const clearPantry = useCallback(async () => {
    setIngredients([]);
    try {
      await clearAllPantryItems();
    } catch (err) {
      console.error('Failed to clear all pantry items:', err);
    }
  }, []);

  const addMultiple = useCallback((newItems: string[]) => {
    newItems.forEach((item) => addIngredient(item));
  }, [addIngredient]);

  const setPantry = useCallback((newItems: string[]) => {
    setIngredients(newItems.map((i) => i.trim().toLowerCase()).filter(Boolean));
  }, []);

  return {
    ingredients,
    setIngredients,
    addIngredient,
    removeIngredient,
    clearPantry,
    addMultiple,
    setPantry,
    refreshPantry,
  };
}
