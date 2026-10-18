import { useCallback, useState } from 'react';
import { fetchRecommendations } from '../services/api';
import { PantryRequest, RecommendationResponse } from '../types/api';
import { PreferencesState } from './usePreferences';

export function useRecommendations() {
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(
    async (
      pantry: string[],
      preferences: PreferencesState,
      limit: number = 10,
      rescueMode: boolean = false,
      queryText?: string | null
    ) => {
      if (!pantry || pantry.length === 0) {
        setError('Please enter at least one pantry ingredient.');
        return;
      }

      setLoading(true);
      setError(null);

      const request: PantryRequest = {
        pantry_ingredients: pantry,
        limit,
        cuisine: preferences.cuisine || null,
        dietary_preference: preferences.dietary || null,
        max_cooking_time_minutes: preferences.maxCookingTime || null,
        allergens: preferences.allergens && preferences.allergens.length > 0 ? preferences.allergens : undefined,
        rescue_mode: rescueMode,
        query_text: queryText || null,
      };

      try {
        const response = await fetchRecommendations(request);
        setData(response);
      } catch (err: any) {
        setError(err.message || 'An error occurred while finding recommendations.');
        setData(null);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const clearResults = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return {
    data,
    loading,
    error,
    search,
    clearResults,
  };
}
