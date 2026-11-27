import { api } from "./client";
import type {
  ApiParams,
  BulkItemsInput,
  BulkItemsResponse,
  CloneRevisionInput,
  Dependency,
  DependencyInput,
  FMEAItem,
  FMEAItemInput,
  Paginated,
  RejectRevisionInput,
  Revision,
  RevisionCreateInput,
  RevisionGraph,
  RevisionReport,
} from "./types";

export async function listRevisions(
  params?: ApiParams,
): Promise<Paginated<Revision>> {
  const { data } = await api.get<Paginated<Revision>>("/revisions/", { params });
  return data;
}

export async function createRevision(
  input: RevisionCreateInput,
): Promise<Revision> {
  const { data } = await api.post<Revision>("/revisions/", input);
  return data;
}

export async function getRevision(id: number): Promise<Revision> {
  const { data } = await api.get<Revision>(`/revisions/${id}/`);
  return data;
}

export async function cloneRevision(
  id: number,
  input: CloneRevisionInput = {},
): Promise<Revision> {
  const { data } = await api.post<Revision>(`/revisions/${id}/clone/`, input);
  return data;
}

export async function submitRevision(id: number): Promise<Revision> {
  const { data } = await api.post<Revision>(`/revisions/${id}/submit/`);
  return data;
}

export async function approveRevision(id: number): Promise<Revision> {
  const { data } = await api.post<Revision>(`/revisions/${id}/approve/`);
  return data;
}

export async function rejectRevision(
  id: number,
  input: RejectRevisionInput,
): Promise<Revision> {
  const { data } = await api.post<Revision>(`/revisions/${id}/reject/`, input);
  return data;
}

export async function archiveRevision(id: number): Promise<Revision> {
  const { data } = await api.post<Revision>(`/revisions/${id}/archive/`);
  return data;
}

export async function listRevisionItems(
  revisionId: number,
  params?: ApiParams,
): Promise<Paginated<FMEAItem>> {
  const { data } = await api.get<Paginated<FMEAItem>>(
    `/revisions/${revisionId}/items/`,
    { params },
  );
  return data;
}

export async function createRevisionItem(
  revisionId: number,
  input: FMEAItemInput,
): Promise<FMEAItem> {
  const { data } = await api.post<FMEAItem>(
    `/revisions/${revisionId}/items/`,
    input,
  );
  return data;
}

export async function bulkUpdateItems(
  revisionId: number,
  input: BulkItemsInput,
): Promise<BulkItemsResponse> {
  const { data } = await api.post<BulkItemsResponse>(
    `/revisions/${revisionId}/items/bulk/`,
    input,
  );
  return data;
}

export async function listItems(
  params?: ApiParams,
): Promise<Paginated<FMEAItem>> {
  const { data } = await api.get<Paginated<FMEAItem>>("/items/", { params });
  return data;
}

export async function getItem(id: number): Promise<FMEAItem> {
  const { data } = await api.get<FMEAItem>(`/items/${id}/`);
  return data;
}

export async function updateItem(
  id: number,
  input: Partial<FMEAItemInput>,
): Promise<FMEAItem> {
  const { data } = await api.patch<FMEAItem>(`/items/${id}/`, input);
  return data;
}

export async function deleteItem(id: number): Promise<void> {
  await api.delete(`/items/${id}/`);
}

export async function listRevisionDependencies(
  revisionId: number,
  params?: ApiParams,
): Promise<Paginated<Dependency>> {
  const { data } = await api.get<Paginated<Dependency>>(
    `/revisions/${revisionId}/dependencies/`,
    { params },
  );
  return data;
}

export async function createRevisionDependency(
  revisionId: number,
  input: DependencyInput,
): Promise<Dependency> {
  const { data } = await api.post<Dependency>(
    `/revisions/${revisionId}/dependencies/`,
    input,
  );
  return data;
}

export async function listDependencies(
  params?: ApiParams,
): Promise<Paginated<Dependency>> {
  const { data } = await api.get<Paginated<Dependency>>("/dependencies/", {
    params,
  });
  return data;
}

export async function deleteDependency(id: number): Promise<void> {
  await api.delete(`/dependencies/${id}/`);
}

export async function getRevisionGraph(id: number): Promise<RevisionGraph> {
  const { data } = await api.get<RevisionGraph>(`/revisions/${id}/graph/`);
  return data;
}

export async function getRevisionReport(
  id: number,
  params?: ApiParams,
): Promise<RevisionReport> {
  const { data } = await api.get<RevisionReport>(`/revisions/${id}/report/`, {
    params,
  });
  return data;
}

export async function downloadRevisionReportXlsx(
  id: number,
  params?: ApiParams,
): Promise<Blob> {
  const { data } = await api.get<Blob>(`/revisions/${id}/report/xlsx/`, {
    params,
    responseType: "blob",
  });
  return data;
}
