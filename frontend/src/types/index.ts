/**
 * TraceShield AI — Shared Frontend Type Definitions.
 * Strictly mirrors the FastAPI contracts defined in api/schemas.py and docs/API_SPEC.md.
 */

export interface PaginationMeta {
  limit: number;
  offset: number;
  total: number;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: any;
  request_id: string;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  dependencies: {
    graph_db: string;
    [key: string]: string;
  };
  timestamp: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  target_type: string;
  target_ref?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ProjectListResponse {
  items: ProjectSummary[];
  pagination: PaginationMeta;
}

export interface FindingSummary {
  id: string;
  project_id: string;
  title: string;
  category: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'informational' | 'unknown';
  severity_level: number;
  status: 'OPEN' | 'CONFIRMED' | 'INCONCLUSIVE' | 'REMEDIATED' | 'REOPENED' | string;
  source: string;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  fingerprint?: string | null;
}

export interface EndpointInfo {
  id: string;
  path: string;
  method: string;
  auth_required: boolean;
}

export interface EvidenceItem {
  id: string;
  summary: string;
  confirmed?: boolean;
  [key: string]: any;
}

export interface ImpactPath {
  website?: string | null;
  endpoint?: string | null;
  service?: string | null;
  database?: string | null;
  asset?: string | null;
  classification?: string | null;
}

export interface PriorityInfo {
  finding_id: string;
  priority_score: number;
  factors?: {
    severity: number;
    exposure: number;
    data_impact: number;
    reachability: number;
  };
  evidence_status?: string;
  note?: string;
}

export interface FindingDetail extends FindingSummary {
  endpoint?: EndpointInfo | null;
  evidence: EvidenceItem[];
  impact_paths: ImpactPath[];
  priority?: PriorityInfo | null;
  guidance?: string | null;
}

export interface FindingListResponse {
  items: FindingSummary[];
  pagination: PaginationMeta;
}

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

export interface GraphMeta {
  node_count: number;
  edge_count: number;
  truncated: boolean;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: GraphMeta;
}

export interface NeighborsResponse {
  node: GraphNode;
  neighbors: GraphNode[];
  edges: GraphEdge[];
  meta: GraphMeta;
}

export interface ScanCreateRequest {
  scanner: string;
  target?: string;
  target_url?: string;
}

export interface ScanResponse {
  id: string;
  project_id: string;
  scanner: string;
  status: 'completed_with_findings' | 'completed_clean' | 'completed' | 'failed' | 'cancelled' | string;
  started_at: string;
  completed_at?: string | null;
  findings_count: number;
  error_summary?: string | null;
  target_url?: string | null;
}

export interface ScanListResponse {
  items: ScanResponse[];
  pagination: PaginationMeta;
}

export interface NextAction {
  action: string;
  target?: string | null;
  why: string;
  method: string;
  requires_approval: boolean;
  verification: string;
  sensitive_assets?: string[];
}

export interface InvestigationRequest {
  project_id: string;
  question: string;
  finding_ids?: string[];
}

export interface InvestigationResponse {
  id: string;
  project_id: string;
  question: string;
  status: string;
  answer: string;
  finding_ids: string[];
  evidence_ids: string[];
  affected_components: Array<{
    finding_id?: string;
    endpoint?: string | null;
    service?: string | null;
    database?: string | null;
    data_asset?: string | null;
    classification?: string | null;
  }>;
  observed_facts: string[];
  inferred_relationships: string[];
  uncertainties: string[];
  next_actions: NextAction[];
  started_at: string;
  completed_at: string;
}

export interface BolaVerificationRequest {
  project_id: string;
  target_url?: string;
}

export interface BolaVerificationResponse {
  test_id: string;
  project_id: string;
  outcome: 'CONFIRMED_UNAUTHORIZED_ACCESS' | 'DENIED_ACCESS' | 'INCONCLUSIVE' | 'ERROR';
  finding_id?: string | null;
  status: string;
  summary: string;
  tested_at: string;
}
