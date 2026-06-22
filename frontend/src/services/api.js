// Lightweight API client for the PolyLife core.
// Served same-origin (Django serves the SPA and the API together), so paths
// are relative and no CORS setup is needed.

const BASE = import.meta.env.VITE_API_BASE ?? '';
const TOKEN_KEY = 'polylife_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = 'GET', body, auth = false } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = {};
  try {
    data = await res.json();
  } catch {
    // response had no JSON body
  }

  if (!res.ok || data.success === false) {
    throw new Error(data.message || 'خطایی رخ داد');
  }
  return data;
}

export function register({ username, password, first_name = '', last_name = '' }) {
  return request('/api/register', {
    method: 'POST',
    body: { username, password, first_name, last_name },
  });
}

export async function login({ username, password }) {
  const data = await request('/api/login', {
    method: 'POST',
    body: { username, password },
  });
  if (data.token) setToken(data.token);
  return data;
}

export function getCurrentUser() {
  return request('/api/user', { auth: true });
}

export async function logout() {
  try {
    await request('/api/logout', { method: 'POST', auth: true });
  } finally {
    clearToken();
  }
}

export function getMicroservices() {
  return request('/api/microservices/');
}
