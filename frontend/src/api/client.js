const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function getApiBaseUrl() {
  const stored = localStorage.getItem('drugtrialai_api_base');
  if (stored !== null) return stored.replace(/\/+$/, '');
  return DEFAULT_API_BASE.replace(/\/+$/, '');
}

export function setApiBaseUrl(url) {
  const cleaned = url.trim().replace(/\/+$/, '');
  if (!cleaned) {
    localStorage.removeItem('drugtrialai_api_base');
  } else {
    localStorage.setItem('drugtrialai_api_base', cleaned);
  }
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function requestJson(path, init) {
  const base = getApiBaseUrl();
  const url = `${base}${path}`;

  let response;
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Network error';
    throw new ApiError(
      0,
      `Unable to reach DrugTrialAI backend (${url}). Ensure FastAPI is running on port 8000. Details: ${message}`
    );
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((item) => {
            if (typeof item === 'object' && item !== null && 'msg' in item) {
              return String(item.msg);
            }
            return JSON.stringify(item);
          })
          .join('; ');
      }
    } catch {
      // Keep status text fallback
    }
    throw new ApiError(response.status, detail);
  }

  return response.json();
}

export const apiClient = {
  checkHealth() {
    return requestJson('/api/v1/health');
  },

  analyzeCase(payload) {
    return requestJson('/api/v1/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  checkDrugInteractions(drugs) {
    return requestJson('/api/v1/drugs/interactions', {
      method: 'POST',
      body: JSON.stringify({ drugs }),
    });
  },

  resolveRxCui(drugName) {
    return requestJson(`/api/v1/drugs/${encodeURIComponent(drugName.trim())}/rxcui`);
  },

  getDrugFdaLabel(drugName) {
    return requestJson(`/api/v1/drugs/${encodeURIComponent(drugName.trim())}/label`);
  },

  searchTrials(params) {
    const qs = new URLSearchParams();
    if (params.condition?.trim()) qs.set('condition', params.condition.trim());
    if (params.intervention?.trim()) qs.set('intervention', params.intervention.trim());
    if (params.phases && params.phases.length > 0) {
      for (const p of params.phases) {
        qs.append('phases', p);
      }
    }
    if (params.status) qs.set('status', params.status);
    if (params.page_size) qs.set('page_size', String(params.page_size));

    return requestJson(`/api/v1/trials/search?${qs.toString()}`);
  },
};
