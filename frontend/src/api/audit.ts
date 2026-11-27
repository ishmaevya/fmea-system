import { api } from "./client";
import type { ApiParams, AuditLog, Paginated } from "./types";

export async function listAuditLogs(
  params?: ApiParams,
): Promise<Paginated<AuditLog>> {
  const { data } = await api.get<Paginated<AuditLog>>("/audit/", { params });
  return data;
}

export async function getAuditLog(id: number): Promise<AuditLog> {
  const { data } = await api.get<AuditLog>(`/audit/${id}/`);
  return data;
}
