const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export function resolveApiUrl(pathOrUrl: string): string {
  if (/^https?:\/\//i.test(pathOrUrl)) {
    return pathOrUrl;
  }
  return `${API_BASE_URL}${pathOrUrl}`;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");

  const response = await fetch(resolveApiUrl(path), {
    ...init,
    headers,
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiError(formatApiError(detail, response.status), response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function apiJson<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  return apiRequest<T>(path, {
    ...init,
    method: init?.method ?? "POST",
    headers,
    body: JSON.stringify(body),
  });
}

function formatApiError(detail: unknown, status: number): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (isObjectWithDetail(detail)) {
    if (typeof detail.detail === "string") {
      return detail.detail;
    }

    if (Array.isArray(detail.detail)) {
      return detail.detail
        .map((entry) => {
          if (isObjectWithMessage(entry)) {
            return entry.msg;
          }
          return String(entry);
        })
        .join(", ");
    }
  }

  return `Request failed with status ${status}`;
}

async function readErrorDetail(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function isObjectWithDetail(value: unknown): value is { detail: unknown } {
  return typeof value === "object" && value !== null && "detail" in value;
}

function isObjectWithMessage(value: unknown): value is { msg: string } {
  return typeof value === "object" && value !== null && "msg" in value && typeof value.msg === "string";
}
