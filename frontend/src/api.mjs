export class Api {
  constructor(token, expired = () => {}, request = fetch) {
    this.token = token;
    this.expired = expired;
    this.request = request;
  }
  /** @param {string} path @param {{method?: string, body?: any, signal?: AbortSignal}} options */
  async call(path, options = {}) {
    let decoded;
    try {
      decoded = decodeURIComponent(path);
    } catch {
      throw new Error("Use an application API path");
    }
    if (typeof path !== "string" || !decoded.startsWith("/api/") || decoded.includes("..") || decoded.includes("\\") || /[\x00-\x20\x7f]/.test(decoded))
      throw new Error("Use an application API path");
    const request = this.request;
    const response = await request(path, {
      method: options.method || "GET",
      redirect: "error",
      signal: options.signal,
      headers: {
        Authorization: "Bearer " + this.token,
        ...(options.body === undefined
          ? {}
          : { "Content-Type": "application/json" }),
      },
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    const data = await response
      .json()
      .catch(() => ({ detail: "The service returned an unreadable response" }));
    if (response.status === 401) this.expired();
    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((item) => item.msg).join("; ")
        : data.detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : "The request could not be completed"
      );
    }
    return data;
  }
}
