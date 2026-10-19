const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function expireSession(token, response) {
  if (response.status !== 401 || !token) return;
  localStorage.removeItem("rrhh-token");
  window.dispatchEvent(new Event("rrhh-session-expired"));
}

export async function api(path, options = {}) {
  const token = localStorage.getItem("rrhh-token");
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !(options.body instanceof URLSearchParams)
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  expireSession(token, response);
  if (!response.ok) {
    const detail = typeof body === "object" && body !== null ? body.detail : body;
    throw new ApiError(detail || `Error ${response.status} al comunicarse con el servidor`, response.status);
  }
  return body;
}

export async function download(path, filename) {
  const token = localStorage.getItem("rrhh-token");
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  expireSession(token, response);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail || `No se pudo descargar el archivo (${response.status})`, response.status);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
