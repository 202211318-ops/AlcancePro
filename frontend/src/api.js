import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8008/api",
  timeout: 60000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("alcancepro_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    config.timeout = 10 * 60 * 1000;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("alcancepro_token");
      if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/registro")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export function getError(error, fallback = "Ocurrió un error") {
  const detail = error?.response?.data?.detail ?? error?.response?.data?.message;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.message || "Error de validación").join(". ");
  }
  return fallback;
}

export default api;
