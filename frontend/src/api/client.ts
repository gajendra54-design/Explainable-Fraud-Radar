let token = sessionStorage.getItem("radar_token") || "";
export const setToken = (value: string) => {
  token = value;
  value
    ? sessionStorage.setItem("radar_token", value)
    : sessionStorage.removeItem("radar_token");
};
export const hasToken = () => Boolean(token);
export async function api<T = unknown>(
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.error?.message || `Request failed (${response.status})`,
    );
  return data;
}
export const number = (v: unknown) =>
  typeof v === "number"
    ? new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(v)
    : "—";
export const percent = (v: unknown) =>
  typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "—";
export const date = (v: string | undefined) =>
  v
    ? new Date(v).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
