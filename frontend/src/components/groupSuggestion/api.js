
const API_BASE = "/api";

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("token");

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
  }

  if (!response.ok) {
    const message =
      (data && (data.message || data.detail)) ||
      "خطا در ارتباط با سرور. لطفاً دوباره تلاش کنید.";
    throw new Error(message);
  }

  return data;
}