const API_ROOT = "/api/v1";

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(path.startsWith("/api") ? path : `${API_ROOT}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      Accept: "application/json",
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });

  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      body?.message || body?.detail || "ارتباط با سرویس ناموفق بود.",
      response.status,
      body?.errors || body,
    );
  }
  return body;
}

export const api = {
  whoami: () => request("/api/whoami"),
  profile: () => request("/profiles/me/"),
  profileById: (userId) => request(`/profiles/${userId}/`),
  updateProfile: (data) =>
    request("/profiles/me/", { method: "PATCH", body: data }),
  profiles: (query = "") => request(`/profiles/?q=${encodeURIComponent(query)}`),
  follow: (userId, follow = true) =>
    request(`/profiles/${userId}/follow/`, { method: follow ? "POST" : "DELETE" }),

  feed: (page = 1) => request(`/posts/feed/?page=${page}`),
  post: (postId) => request(`/posts/${postId}/`),
  postsByAuthor: (userId) => request(`/posts/?author_id=${userId}&page_size=50`),
  explore: (query = "") => request(`/posts/explore/?q=${encodeURIComponent(query)}`),
  createPost: (formData) => request("/posts/", { method: "POST", body: formData }),
  like: (postId, liked) =>
    request(`/posts/${postId}/like/`, { method: liked ? "DELETE" : "POST" }),
  comments: (postId) => request(`/posts/${postId}/comments/`),
  addComment: (postId, data) =>
    request(`/posts/${postId}/comments/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  reportPost: (postId, reason) =>
    request(`/posts/${postId}/report/`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  categories: () => request("/categories/?page_size=50"),
  contents: (params = "") => request(`/contents/?${params}`),
  createContent: (formData) =>
    request("/contents/", { method: "POST", body: formData }),
  rateContent: (id, score) =>
    request(`/contents/${id}/rate/`, {
      method: "PUT",
      body: JSON.stringify({ score }),
    }),

  courses: (params = "") => request(`/courses/?${params}`),
  course: (id) => request(`/courses/${id}/`),
  enroll: (id) => request(`/courses/${id}/enroll/`, { method: "POST", body: "{}" }),
  enrollments: () => request("/enrollments/?page_size=50"),
  updateLesson: (enrollmentId, lessonId, data) =>
    request(`/enrollments/${enrollmentId}/lessons/${lessonId}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  activity: (scope = "me") => request(`/activity/?scope=${encodeURIComponent(scope)}`),

  messageThreads: () => request("/messages/"),
  messageThread: (userId) => request(`/messages/with/${userId}/`),
  sendMessage: (userId, body) =>
    request(`/messages/with/${userId}/`, {
      method: "POST",
      body: JSON.stringify({ body }),
    }),

  cart: () => request("/cart/"),
  addToCart: (courseId) =>
    request("/cart/", {
      method: "POST",
      body: JSON.stringify({ course_id: courseId }),
    }),
  removeFromCart: (itemId) => request(`/cart/${itemId}/`, { method: "DELETE" }),
  checkout: () => request("/cart/checkout/", { method: "POST", body: "{}" }),
  purchases: () => request("/purchases/?page_size=50"),

  logout: async () => {
    const response = await fetch("/auth/logout", {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new ApiError("خروج از حساب ناموفق بود.", response.status);
    return response.json().catch(() => ({}));
  },
};

export function results(payload) {
  return Array.isArray(payload) ? payload : payload?.results || [];
}
