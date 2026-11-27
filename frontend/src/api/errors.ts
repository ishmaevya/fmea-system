import { AxiosError } from "axios";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function extractMessage(value: unknown): string | null {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value) && typeof value[0] === "string") {
    return value[0];
  }
  return null;
}

export function getErrorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) {
    return error instanceof Error ? error.message : "Неизвестная ошибка";
  }

  const data: unknown = error.response?.data;
  if (isRecord(data)) {
    const detail = extractMessage(data.detail);
    if (detail) {
      return detail;
    }
    for (const value of Object.values(data)) {
      const message = extractMessage(value);
      if (message) {
        return message;
      }
    }
  }

  return error.message || "Ошибка запроса";
}
