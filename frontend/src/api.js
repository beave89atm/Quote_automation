import { TOKEN_KEY } from "./auth";

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.set("X-App-Token", token);
  if (options.json) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, {
    ...options,
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
            detail = data.detail || JSON.stringify(data);
            if (detail && typeof detail === "object") {
              detail = detail.error || detail.message || JSON.stringify(detail);
            }
    } catch {
      /* ignore */
    }
    if (res.status === 401 && !path.includes("/api/login")) {
      localStorage.removeItem(TOKEN_KEY);
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}
