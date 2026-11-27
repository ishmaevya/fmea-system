export type Role = "engineer" | "quality" | "admin";
export type ProductStatus = "active" | "archived";
export type Criticality = "low" | "medium" | "high" | "critical";
export type RevisionStatus = "draft" | "review" | "approved" | "archived";
export type ItemStatus = "open" | "in_progress" | "done" | "accepted";
export type ItemSource = "manual" | "llm";
export type DependencyType = "causes" | "affects" | "mitigates";
export type SuggestionStatus = "new" | "applied" | "rejected";
export type ActionPriority = "low" | "medium" | "high" | "critical";

export type ApiParams = Record<string, string | number | boolean | null | undefined>;

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  position: string;
  is_active: boolean;
}

export interface Product {
  id: number;
  code: string;
  name: string;
  manufacturer: string;
  tu_code: string;
  description: string;
  status: ProductStatus;
  created_by: number;
  created_by_email: string;
  variants_count: number;
  components_count: number;
  revisions_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProductInput {
  code: string;
  name: string;
  manufacturer?: string;
  tu_code?: string;
  description?: string;
  status?: ProductStatus;
}

export interface ProductVariant {
  id: number;
  product: number;
  code: string;
  name: string;
  settings: Record<string, unknown>;
  is_default: boolean;
  components_count: number;
  created_at: string;
}

export interface VariantInput {
  product?: number;
  code: string;
  name: string;
  settings?: Record<string, unknown>;
  is_default?: boolean;
}

export interface Component {
  id: number;
  product: number;
  variant: number | null;
  parent: number | null;
  code: string;
  name: string;
  component_type: string;
  description: string;
  criticality: Criticality;
  is_active: boolean;
  children_count: number;
  fmea_items_count: number;
  created_at: string;
  updated_at: string;
}

export interface ComponentInput {
  product?: number;
  variant?: number | null;
  parent?: number | null;
  code: string;
  name: string;
  component_type?: string;
  description?: string;
  criticality?: Criticality;
  is_active?: boolean;
}

export interface Revision {
  id: number;
  product: number;
  product_code: string;
  product_name: string;
  variant: number | null;
  variant_code: string | null;
  version: string;
  status: RevisionStatus;
  status_display: string;
  based_on: number | null;
  change_reason: string;
  created_by: number;
  created_by_email: string;
  approved_by: number | null;
  approved_by_email: string | null;
  approved_at: string | null;
  items_count: number;
  dependencies_count: number;
  created_at: string;
  updated_at: string;
}

export interface RevisionCreateInput {
  product: number;
  variant?: number | null;
  version?: string;
  change_reason?: string;
  based_on?: number | null;
}

export interface CloneRevisionInput {
  version?: string;
  change_reason?: string;
}

export interface RejectRevisionInput {
  reason: string;
}

export interface FMEAItem {
  id: number;
  revision: number;
  revision_status: RevisionStatus;
  component: number;
  component_code: string;
  component_name: string;
  failure_mode: string;
  failure_cause: string;
  failure_effect: string;
  severity: number;
  occurrence: number;
  detection: number;
  rpn: number;
  action_priority: ActionPriority;
  action_priority_display: string;
  recommended_action: string;
  responsible: number | null;
  responsible_email: string | null;
  due_date: string | null;
  status: ItemStatus;
  status_display: string;
  source: ItemSource;
  source_display: string;
  source_reference: string;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface FMEAItemInput {
  component: number;
  failure_mode: string;
  failure_cause: string;
  failure_effect: string;
  severity: number;
  occurrence: number;
  detection: number;
  recommended_action?: string;
  responsible?: number | null;
  due_date?: string | null;
  status?: ItemStatus;
}

export interface BulkItemsInput {
  items: Array<FMEAItemInput & { id?: number }>;
  deleted_ids?: number[];
}

export interface BulkItemsResponse {
  items: FMEAItem[];
  created: number;
  updated: number;
  deleted: number;
}

export interface Dependency {
  id: number;
  revision: number;
  source_item: number;
  source_mode: string;
  target_item: number;
  target_mode: string;
  relation_type: DependencyType;
  relation_type_display: string;
  description: string;
  created_at: string;
}

export interface DependencyInput {
  source_item: number;
  target_item: number;
  relation_type: DependencyType;
  description?: string;
}

export interface GraphNode {
  id: number;
  component_id: number;
  component_code: string;
  component_name: string;
  failure_mode: string;
  rpn: number;
  action_priority: ActionPriority;
  action_priority_display: string;
  severity: number;
  status: ItemStatus;
}

export interface GraphEdge {
  id: number;
  source: number;
  target: number;
  relation_type: DependencyType;
  relation_type_display: string;
  description: string;
}

export interface RevisionGraph {
  revision: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Attachment {
  id: number;
  product: number | null;
  revision: number | null;
  item: number | null;
  original_name: string;
  content_type: string;
  size: number;
  uploaded_by: number;
  uploaded_by_email: string;
  download_url: string | null;
  created_at: string;
}

export interface AttachmentDownload {
  url: string;
  expires_in: number;
}

export interface SuggestionResponse {
  disclaimer: string;
  suggestions: Array<{
    failure_mode: string;
    failure_cause: string;
    failure_effect: string;
    severity: number;
    occurrence: number;
    detection: number;
    recommended_action: string;
    source_reference: string;
  }>;
}

export interface Suggestion {
  id: number;
  product: number;
  revision: number | null;
  component: number;
  component_code: string;
  component_name: string;
  prompt: string;
  response: SuggestionResponse;
  provider: string;
  model_name: string;
  status: SuggestionStatus;
  status_display: string;
  applied_item: number | null;
  created_by: number;
  created_by_email: string;
  created_at: string;
}

export interface SuggestionInput {
  revision: number;
  component: number;
  hints?: string;
}

export interface ReportRevision {
  id: number;
  product: number;
  product_code: string;
  product_name: string;
  variant_code: string | null;
  version: string;
  status: RevisionStatus;
  status_display: string;
}

export interface ReportSummary {
  items_count: number;
  components_count: number;
  avg_rpn: number;
  max_rpn: number;
  counts_by_priority: Record<string, number>;
  counts_by_status: Record<string, number>;
}

export interface TopRisk {
  id: number;
  component_id: number;
  component_code: string;
  component_name: string;
  failure_mode: string;
  failure_cause: string;
  failure_effect: string;
  severity: number;
  occurrence: number;
  detection: number;
  rpn: number;
  action_priority: ActionPriority;
  action_priority_display: string;
  recommended_action: string;
  responsible_email: string | null;
  due_date: string | null;
  status: ItemStatus;
  status_display: string;
  source: ItemSource;
}

export interface RevisionReport {
  revision: ReportRevision;
  summary: ReportSummary;
  top_risks: TopRisk[];
  generated_at: string;
}

export interface AuditLog {
  id: number;
  user: number | null;
  user_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}
