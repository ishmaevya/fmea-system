import { api } from "./client";
import type {
  ApiParams,
  Attachment,
  AttachmentDownload,
  Paginated,
} from "./types";

export type AttachmentTarget =
  | { product: number }
  | { revision: number }
  | { item: number };

export async function listAttachments(
  params?: ApiParams,
): Promise<Paginated<Attachment>> {
  const { data } = await api.get<Paginated<Attachment>>("/attachments/", {
    params,
  });
  return data;
}

export async function uploadAttachment(
  file: File,
  target: AttachmentTarget,
): Promise<Attachment> {
  const body = new FormData();
  body.append("file", file);
  for (const [key, value] of Object.entries(target)) {
    body.append(key, String(value));
  }

  const { data } = await api.post<Attachment>("/attachments/", body);
  return data;
}

export async function getAttachment(id: number): Promise<Attachment> {
  const { data } = await api.get<Attachment>(`/attachments/${id}/`);
  return data;
}

export async function getAttachmentDownload(
  id: number,
): Promise<AttachmentDownload> {
  const { data } = await api.get<AttachmentDownload>(
    `/attachments/${id}/download/`,
  );
  return data;
}

export async function deleteAttachment(id: number): Promise<void> {
  await api.delete(`/attachments/${id}/`);
}
