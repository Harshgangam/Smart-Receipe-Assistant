import { useCallback, useState } from 'react';

export interface PreferencesState {
  cuisine: string | null;
  dietary: string | null;
  maxCookingTime: number | null;
  allergens?: string[];
}

export function usePreferences() {
  const [cuisine, setCuisine] = useState<string | null>(null);
  const [dietary, setDietary] = useState<string | null>(null);
  const [maxCookingTime, setMaxCookingTime] = useState<number | null>(null);
  const [allergens, setAllergens] = useState<string[]>([]);

  const addAllergen = useCallback((allergen: string) => {
    const trimmed = allergen.trim().toLowerCase();
    if (trimmed && !allergens.includes(trimmed)) {
      setAllergens((prev) => [...prev, trimmed]);
    }
  }, [allergens]);

  const removeAllergen = useCallback((allergen: string) => {
    setAllergens((prev) => prev.filter((a) => a.toLowerCase() !== allergen.toLowerCase()));
  }, []);

  const resetPreferences = useCallback(() => {
    setCuisine(null);
    setDietary(null);
    setMaxCookingTime(null);
    setAllergens([]);
  }, []);

  return {
    cuisine,
    setCuisine,
    dietary,
    setDietary,
    maxCookingTime,
    setMaxCookingTime,
    allergens,
    setAllergens,
    addAllergen,
    removeAllergen,
    resetPreferences,
  };
}
