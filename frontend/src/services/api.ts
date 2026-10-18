import {
  AssistantRequest,
  AssistantResponse,
  AssistantStatusResponse,
  HealthResponse,
  PantryRequest,
  RecommendationResponse,
  SustainabilityMetricsResponse,
} from '../types/api';
import { PantryItem } from '../types/recipe';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

let activeApiHost = API_BASE || '';

/**
 * Resilient fetch helper that automatically tries the current origin (Vite proxy),
 * followed by direct FastAPI localhost backends (127.0.0.1:8000 and localhost:8000)
 * with CORS support. Caches the functional host for instant subsequent calls.
 */
export async function fetchApi(path: string, options?: RequestInit): Promise<Response> {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const candidates: string[] = [];

  // Try direct 127.0.0.1 first (fastest on Windows), then active host, then relative proxy
  candidates.push(`http://127.0.0.1:8000${normalizedPath}`);
  if (activeApiHost && !activeApiHost.includes('127.0.0.1:8000')) {
    candidates.push(`${activeApiHost}${normalizedPath}`);
  }
  candidates.push(normalizedPath);
  candidates.push(`http://localhost:8000${normalizedPath}`);

  const uniqueCandidates = Array.from(new Set(candidates));
  let lastError: any = null;

  for (const candidate of uniqueCandidates) {
    try {
      const res = await fetch(candidate, options);
      if (res.ok || res.status < 500) {
        if (candidate.startsWith('http')) {
          try {
            activeApiHost = new URL(candidate).origin;
          } catch {}
        }
        return res;
      }
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error('Unable to connect to backend server');
}

export class ApiServiceError extends Error {
  status?: number;
  details?: any;

  constructor(message: string, status?: number, details?: any) {
    super(message);
    this.name = 'ApiServiceError';
    this.status = status;
    this.details = details;
  }
}

export async function fetchRecommendations(
  request: PantryRequest
): Promise<RecommendationResponse> {
  try {
    const response = await fetchApi('/api/recommendations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      let errorMsg = `Server error (${response.status})`;
      let details: any = null;
      try {
        const errorData = await response.json();
        details = errorData;
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMsg = errorData.detail.map((e: any) => e.msg || e).join(', ');
          } else {
            errorMsg = String(errorData.detail);
          }
        }
      } catch {
        // Fall back
      }
      throw new ApiServiceError(errorMsg, response.status, details);
    }

    return (await response.json()) as RecommendationResponse;
  } catch (err: any) {
    if (err instanceof ApiServiceError) {
      throw err;
    }
    throw new ApiServiceError(
      'Unable to connect to the backend server. Please verify that the FastAPI backend is running.'
    );
  }
}

export async function fetchRecipeById(recipeId: number, pantry?: string[]): Promise<any> {
  const query = pantry && pantry.length > 0
    ? `?${pantry.map((p) => `pantry=${encodeURIComponent(p)}`).join('&')}`
    : '';
  const response = await fetchApi(`/api/recipes/${recipeId}${query}`);
  if (!response.ok) {
    throw new ApiServiceError(`Failed to fetch recipe details (${response.status})`);
  }
  return await response.json();
}


export async function fetchPantryItems(): Promise<PantryItem[]> {
  try {
    const response = await fetchApi('/api/pantry/items');
    if (!response.ok) return [];
    return (await response.json()) as PantryItem[];
  } catch {
    return [];
  }
}

export async function addPantryItem(item: { name: string; category?: string; quantity?: number; unit?: string; expiry_days?: number }): Promise<PantryItem> {
  const response = await fetchApi('/api/pantry/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item),
  });
  return (await response.json()) as PantryItem;
}

export async function deletePantryItem(itemId: string): Promise<void> {
  await fetchApi(`/api/pantry/items/${itemId}`, { method: 'DELETE' });
}

export async function cookRecipe(recipeId: number, title: string, ner: string[]): Promise<any> {
  const response = await fetchApi('/api/pantry/cook', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipe_id: recipeId, recipe_title: title, recipe_ner: ner }),
  });
  return await response.json();
}

export async function scanPantryImage(): Promise<any> {
  const response = await fetchApi('/api/pantry/scan-image', { method: 'POST' });
  return await response.json();
}

export async function fetchSustainabilityAnalytics(): Promise<SustainabilityMetricsResponse> {
  const response = await fetchApi('/api/analytics/sustainability');
  return (await response.json()) as SustainabilityMetricsResponse;
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  try {
    const response = await fetchApi('/health', { method: 'GET' });
    if (response.ok) {
      return (await response.json()) as HealthResponse;
    }
  } catch {
    // Continue
  }

  throw new ApiServiceError('Backend is currently offline or unreachable.');
}

export async function askRecipeAssistant(
  request: AssistantRequest
): Promise<AssistantResponse> {
  const response = await fetchApi('/api/assistant/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new ApiServiceError(`Assistant error (${response.status})`);
  }

  return (await response.json()) as AssistantResponse;
}

export async function fetchAssistantStatus(): Promise<AssistantStatusResponse> {
  const response = await fetchApi('/api/assistant/status', { method: 'GET' });
  if (!response.ok) {
    throw new ApiServiceError(`Status check failed (${response.status})`);
  }
  return (await response.json()) as AssistantStatusResponse;
}

export async function simulateSandbox(payload: any): Promise<any> {
  const response = await fetchApi('/api/sandbox/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiServiceError(`Sandbox simulation error (${response.status})`);
  }
  return await response.json();
}

export async function fetchMicroShoppingPlan(recipeCandidates: any[]): Promise<any> {
  const response = await fetchApi('/api/shopping/optimize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipe_candidates: recipeCandidates }),
  });
  if (!response.ok) {
    throw new ApiServiceError(`Shopping optimization error (${response.status})`);
  }
  return await response.json();
}
