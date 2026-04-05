/**
 * Acadex API Client
 * Centralised fetch wrapper for all API calls
 */

(() => {
  if (window.ApiClient) return;

  const isLocalhost =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname.endsWith(".local");
  const DEFAULT_API_BASE_URL = isLocalhost
    ? `http://${window.location.hostname}:8080/api`
    : `${window.location.origin}/api`;
  const API_BASE_URL = window.ACADEX_API_BASE_URL || DEFAULT_API_BASE_URL;

  class ApiClient {
    static async request(endpoint, options = {}) {
    // Wait for Auth to initialize if needed
    const user = await new Promise((resolve) => {
      const unsubscribe = firebase.auth().onAuthStateChanged((user) => {
        unsubscribe();
        resolve(user);
      });
    });

    const token = user ? await user.getIdToken() : null;
    if (!token) throw new Error("Missing or invalid Authorization header");

    const headers = {
      "Content-Type": "application/json",
      ...(token && { "Authorization": `Bearer ${token}` }),
      ...options.headers
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Something went wrong");
    }

    return response.json();
  }

    static get(endpoint) {
      return this.request(endpoint, { method: "GET" });
    }

    static post(endpoint, body) {
      return this.request(endpoint, {
        method: "POST",
        body: JSON.stringify(body)
      });
    }

    static put(endpoint, body) {
      return this.request(endpoint, {
        method: "PUT",
        body: JSON.stringify(body)
      });
    }

    static delete(endpoint) {
      return this.request(endpoint, { method: "DELETE" });
    }
  }

  window.ApiClient = ApiClient;
})();
