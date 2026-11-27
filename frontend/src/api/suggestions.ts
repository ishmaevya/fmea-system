import { api } from "./client";
import type {
  ApiParams,
  FMEAItem,
  Paginated,
  Suggestion,
  SuggestionInput,
} from "./types";

export async function listSuggestions(
  params?: ApiParams,
): Promise<Paginated<Suggestion>> {
  const { data } = await api.get<Paginated<Suggestion>>("/suggestions/", {
    params,
  });
  return data;
}

export async function createSuggestion(
  input: SuggestionInput,
): Promise<Suggestion> {
  const { data } = await api.post<Suggestion>("/suggestions/", input);
  return data;
}

export async function getSuggestion(id: number): Promise<Suggestion> {
  const { data } = await api.get<Suggestion>(`/suggestions/${id}/`);
  return data;
}

export async function applySuggestion(id: number): Promise<FMEAItem> {
  const { data } = await api.post<FMEAItem>(`/suggestions/${id}/apply/`);
  return data;
}

export async function rejectSuggestion(id: number): Promise<Suggestion> {
  const { data } = await api.post<Suggestion>(`/suggestions/${id}/reject/`);
  return data;
}
