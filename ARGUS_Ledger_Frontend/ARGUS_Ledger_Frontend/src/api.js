export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export function apiUrl(path) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      ...(options.body ? {"Content-Type": "application/json"} : {}),
      ...(options.headers || {})
    }
  });

  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; }
  catch { data = text; }

  if (!response.ok) {
    const detail = data?.detail ?? data?.message ?? data?.error ?? text ?? `HTTP ${response.status}`;
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail, null, 2));
    err.status = response.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  health: () => request("/health"),
  dashboard: () => request("/dashboard"),
  decisions: () => request("/decisions"),
  decision: (id) => request(`/decisions/${encodeURIComponent(id)}`),
  evidence: (id) => request(`/decisions/${encodeURIComponent(id)}/evidence`),
  audit: (id) => request(`/decisions/${encodeURIComponent(id)}/audit`),

  createDecision: (payload) => request("/decisions", {
    method: "POST", body: JSON.stringify(payload)
  }),

  generateDecision: (payload) => request("/decisions/generate", {
    method: "POST", body: JSON.stringify(payload)
  }),

  reviewDecision: (id, payload) => request(`/decisions/${encodeURIComponent(id)}/review`, {
    method: "POST", body: JSON.stringify(payload)
  }),

  verifyText: (payload) => request("/verification/text", {
    method: "POST", body: JSON.stringify(payload)
  }),

  verifyUrl: (payload) => request("/verification/url", {
    method: "POST", body: JSON.stringify(payload)
  }),

  verifyImage: async (file, fields = {}) => {
    const form = new FormData();
    form.append("file", file);
    Object.entries(fields).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") form.append(key, value);
    });
    const response = await fetch(apiUrl("/verification/image"), { method: "POST", body: form });
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    if (!response.ok) {
      const detail = data?.detail ?? data?.message ?? text ?? `HTTP ${response.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail, null, 2));
    }
    return data;
  }
};

export function pretty(value) {
  if (value === undefined || value === null) return "—";
  if (typeof value === "string") return value;
  try { return JSON.stringify(value, null, 2); } catch { return String(value); }
}

export function pick(obj, keys, fallback = "—") {
  for (const key of keys) {
    if (obj?.[key] !== undefined && obj?.[key] !== null && obj?.[key] !== "") return obj[key];
  }
  return fallback;
}