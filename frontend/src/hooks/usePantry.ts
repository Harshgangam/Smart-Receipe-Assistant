import { useCallback, useEffect, useState } from 'react';
import { addPantryItem, deletePantryItem, deletePantryItemByName, fetchPantryItems } from '../services/api';

export function usePantry(initialIngredients: string[] = []) {
  const [ingredients, setIngredients] = useState<string[]>(initialIngredients);

  // 1. Initial sync: load existing items from Pantry Intelligence into Kitchen Pantry
  useEffect(() => {
    fetchPantryItems()
      .then((items) => {
        if (items && items.length > 0) {
          const names = items.map((i) => i.name.toLowerCase().trim());
          setIngredients((prev) => Array.from(new Set([...prev, ...names])));
        }
      })
      .catch((err) => console.error('Failed to load initial pantry items:', err));
  }, []);

  // 2. Add ingredient: updates Photo 1 immediately and persists to Photo 2 (Pantry Intelligence)
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

  // 3. Remove ingredient: removes from Photo 1 AND deletes from Photo 2 (Pantry Intelligence)
  const removeIngredient = useCallback((itemToRemove: string) => {
    const cleanName = itemToRemove.trim().toLowerCase();
    // Remove from local UI state (Photo 1)
    setIngredients((prev) =>
      prev.filter((i) => i.toLowerCase() !== cleanName)
    );
    // Delete from backend pantry (Photo 2)
    deletePantryItemByName(cleanName);
  }, []);

  // 4. Clear all ingredients: clears both Photo 1 and Photo 2
  const clearPantry = useCallback(async () => {
    setIngredients([]);
    try {
      const items = await fetchPantryItems();
      await Promise.all(items.map((item) => deletePantryItem(item.id)));
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
  };
}
