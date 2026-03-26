import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "./store";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Queue for requests waiting while a token refresh is in flight
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else if (token) resolve(token);
  });
  failedQueue = [];
};

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401: refresh once, retry, or redirect to login
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    // If already refreshing, queue this request
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      });
    }

    original._retry = true;
    isRefreshing = true;

    const refreshToken = useAuthStore.getState().refreshToken;
    if (!refreshToken) {
      useAuthStore.getState().clearAuth();
      if (typeof window !== "undefined") window.location.href = "/login";
      return Promise.reject(error);
    }

    try {
      const res = await axios.post(`${BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const { access_token, refresh_token } = res.data.data;
      useAuthStore.getState().setTokens(access_token, refresh_token);
      api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
      processQueue(null, access_token);
      original.headers.Authorization = `Bearer ${access_token}`;
      return api(original);
    } catch (err) {
      processQueue(err, null);
      useAuthStore.getState().clearAuth();
      if (typeof window !== "undefined") window.location.href = "/login";
      return Promise.reject(err);
    } finally {
      isRefreshing = false;
    }
  }
);

// Typed API helpers
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  register: (email: string, password: string) =>
    api.post("/auth/register", { email, password }),
  logout: () => api.post("/auth/logout"),
};

export const conversationsApi = {
  list: () => api.get("/conversations/"),
  create: (title?: string) => api.post("/conversations/", { title }),
  messages: (id: string) => api.get(`/conversations/${id}/messages`),
  // Returns URL + auth header object for use with fetch() streaming
  streamFetch: (id: string, query: string) => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = useAuthStore.getState().accessToken;
    const url = `${base}/conversations/${id}/stream?${new URLSearchParams({ query })}`;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return { url, headers };
  },
};

export const documentsApi = {
  list: () => api.get("/documents/"),
  upload: (
    file: File,
    visibility: "global" | "private",
    onProgress?: (pct: number) => void
  ) => {
    const form = new FormData();
    form.append("file", file);
    form.append("visibility", visibility);
    return api.post("/documents/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    });
  },
  delete: (id: string) => api.delete(`/documents/${id}`),
};

export const shareApi = {
  createLink: (data: { label?: string; expires_at?: string }) =>
    api.post("/share/links", data),
  listLinks: () => api.get("/share/links"),
  updateLink: (token: string, data: { is_active?: boolean; label?: string }) =>
    api.patch(`/share/links/${token}`, data),
  deleteLink: (token: string) => api.delete(`/share/links/${token}`),
};

export const publicShareApi = {
  getLink: (token: string) => axios.get(`${BASE_URL}/share/${token}`),
  createConversation: (token: string) =>
    axios.post(`${BASE_URL}/share/${token}/conversations`),
  getMessages: (token: string, convId: string) =>
    axios.get(`${BASE_URL}/share/${token}/conversations/${convId}/messages`),
  streamUrl: (token: string, convId: string, query: string) =>
    `${BASE_URL}/share/${token}/conversations/${convId}/stream?query=${encodeURIComponent(query)}`,
};
