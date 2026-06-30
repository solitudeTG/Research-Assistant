import { apiClient, ApiResponse, createSSEConnection, SSECallbacks } from './client';
import type { FileInfo } from './file';
import type { EvidenceAdmissionMetadata, ResearchTaskRouteMetadata, RoundFileInfo, SourceQualityMetadata, ToolRuntimeResultSummary } from '../types/event';
import { ListSessionItem, GetSessionResponse, ExternalSkillItem, ExternalToolItem } from '../types/response';

// Re-export or alias if needed for backward compatibility, 
// but prefer using types from response.ts to ensure consistency.
export type Session = ListSessionItem; 
export type SessionDetail = GetSessionResponse;

export interface CreateSessionRequest {
  mode: string;
  model_config_id?: string;
}

export interface ChatRequest {
  message: string;
  timestamp?: number;
  event_id?: string;
  attachments?: string[];
  language?: string;
  model_config_id?: string;
  active_tool_packs?: string[];
}

export interface ResearchCitation {
  evidence_id: number;
  chunk_id: string;
  paper_id: string;
  title: string;
  section: string;
  page_start?: number | null;
  page_end?: number | null;
  quote: string;
  citation_label: string;
  source_type: 'paper' | 'web' | 'database';
  evidence_scope?: 'session' | 'project' | string;
}

export interface ResearchContextMemory {
  memory_id: string;
  layer: 'l1' | 'l2' | 'l3' | string;
  title: string;
  content: string;
  source_type: 'memory';
  context_only: true;
  source_subject_type?: string | null;
  source_subject_id?: string | null;
  relevance_score?: number;
  recall_reason?: string;
  memory_status?: 'active' | 'conflict';
  conflicts_with?: string[];
}

export interface ResearchContextBoundaries {
  citation_evidence: ('paper' | 'web' | 'database' | string)[];
  context_only_memory: ('memory' | string)[];
  process_trace: string[];
  model_reasoning: ('model_reasoning' | string)[];
}

export interface ResearchPromotedMemory extends ResearchContextMemory {
  session_id: string;
  promotion_reason: 'approved_audit_claim' | string;
  evidence_ids: number[];
  created: boolean;
  duplicate: boolean;
}

export interface ResearchDeletedMemory {
  memory_id: string;
  session_id: string;
  deleted: boolean;
  source_type: 'memory';
  context_only: true;
}

export interface ResearchEvidenceRecord {
  evidence_id: number;
  evidence_type: 'paper' | 'web' | 'database';
  chunk_id: string;
  paper_id: string;
  title: string;
  section: string;
  page_start?: number | null;
  page_end?: number | null;
  quote: string;
  chunk_content: string;
  source_identity: Record<string, unknown>;
}

export interface ResearchAuditClaim {
  claim_text: string;
  status: 'approved' | 'unsupported' | 'invalid_source';
  evidence_ids: number[];
  notes: string[];
  support_score?: number;
}

export interface ResearchAudit {
  status: 'approved' | 'partial' | 'unsupported' | 'invalid_source';
  claim_count: number;
  approved_claim_count: number;
  unsupported_claim_count: number;
  invalid_source_count: number;
  boundaries: {
    citation_evidence: string[];
    context_only: string[];
  };
  claims: ResearchAuditClaim[];
}

export interface ResearchSummarySynthesis {
  mode?: 'llm_section_global' | 'deterministic_extractive' | 'no_citation_evidence' | string;
  intermediate_sources?: string[];
  intermediate_boundary?: 'context_only' | string;
  citation_source?: 'original_evidence' | string;
  section_count?: number;
}

export interface ResearchAnswer {
  answer_id: string;
  content: string;
  citations: ResearchCitation[];
  citation_count: number;
  context_memory?: ResearchContextMemory[];
  context_memory_count?: number;
  context_memory_conflict_count?: number;
  context_boundaries?: ResearchContextBoundaries;
  evidence_admission?: EvidenceAdmissionMetadata;
  summary_synthesis?: ResearchSummarySynthesis;
  task_route?: ResearchTaskRouteMetadata;
  audit?: ResearchAudit;
  question?: string;
}

export interface ResearchReportReaderSummary {
  status: string;
  evidence_basis: string;
  memory_boundary: string;
  next_action: string;
}

export interface ResearchReport {
  report_id: string;
  title: string;
  question: string;
  markdown_path: string;
  evidence_map_path: string;
  citation_count: number;
  reader_summary?: ResearchReportReaderSummary;
  round_files?: RoundFileInfo[];
}

export interface ResearchSessionStatus {
  session_id: string;
  paper_count: number;
  chunk_count: number;
  has_indexed_papers: boolean;
}

export interface ResearchProject {
  project_id: string;
  user_id: string;
  name: string;
  description: string;
  paper_count: number;
  chunk_count: number;
  evidence_record_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ResearchProjectPaperAsset {
  paper_id: string;
  project_id: string;
  session_id: string;
  user_id: string;
  title: string;
  authors: string[];
  abstract: string;
  source_path: string;
  parser: string;
  source_identity: Record<string, unknown>;
  chunk_count: number;
  evidence_record_count: number;
  status: 'uploaded' | 'parsed' | 'indexed' | string;
  citation_ready: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ResearchProjectPaperUploadResult {
  project_id: string;
  paper_id: string;
  title: string;
  authors: string[];
  parser: string;
  chunk_count: number;
  evidence_record_count: number;
  embedding_count: number;
  embedding_model: string;
  status: 'indexed' | string;
  citation_ready: boolean;
  manifest_path: string;
  evidence_preview_path: string;
}

export interface ResearchLibraryPromotionResult extends ResearchProjectPaperUploadResult {
  source_session_id: string;
  source_path: string;
  library_path: string;
  promotion_status: 'indexed' | string;
}

export interface SessionResearchProjectBinding {
  session_id: string;
  project: ResearchProject | null;
}

export interface SourceEvidenceChunkPayload {
  section: string;
  content: string;
  quote?: string;
}

export interface WebEvidenceIngestPayload {
  url: string;
  title: string;
  retrieved_at?: string;
  chunks: SourceEvidenceChunkPayload[];
}

export interface DatabaseEvidenceIngestPayload {
  database_name: string;
  query: string;
  title: string;
  retrieved_at?: string;
  chunks: SourceEvidenceChunkPayload[];
}

export interface SourceEvidenceIngestResult {
  source_type: 'web' | 'database';
  source_id: string;
  title: string;
  retrieved_at: string;
  chunk_count: number;
  evidence_record_count: number;
  source_quality: SourceQualityMetadata;
  url?: string;
  database_name?: string;
  query?: string;
}

export interface RuntimeResultAuditItem {
  event_id?: string;
  timestamp?: number;
  tool_call_id?: string;
  name?: string;
  function?: string;
  status?: 'calling' | 'called' | string;
  summary: ToolRuntimeResultSummary;
}

export interface RuntimeResultAuditFilters {
  tool_pack_id?: string;
  result_sha256?: string;
}

export interface RuntimeResultAuditExportManifest {
  format: 'runtime_result_audit.v1';
  session_id: string;
  runtime_result_count: number;
  filters: RuntimeResultAuditFilters;
  context_boundary: 'process_trace';
  citation_evidence: false;
  event_ids: string[];
}

export interface RuntimeResultAudit {
  session_id: string;
  runtime_result_count: number;
  runtime_results: RuntimeResultAuditItem[];
  context_boundary: 'process_trace';
  citation_evidence: false;
  export_manifest: RuntimeResultAuditExportManifest;
}

export interface RuntimeResultAuditExport extends RuntimeResultAudit {
  artifact_path: string;
  file_url: string;
  round_files: RoundFileInfo[];
}

export async function createSession(data: CreateSessionRequest): Promise<Session> {
  const response = await apiClient.put<ApiResponse<Session>>('/sessions', data);
  return response.data.data;
}

export async function listSessions(): Promise<Session[]> {
  const response = await apiClient.get<ApiResponse<{sessions: Session[]}>>('/sessions');
  return response.data.data.sessions;
}

export function listSessionsSSE(callbacks: SSECallbacks<any>): Promise<() => void> {
  // Note: backend does not have an SSE endpoint for session listing.
  // This function is kept for compatibility but should not be used in production.
  return createSSEConnection('/sessions', { method: 'GET' }, callbacks);
}

export function subscribeSessionNotifications(callbacks: SSECallbacks<any>): Promise<() => void> {
  return createSSEConnection('/sessions/notifications', { method: 'GET' }, callbacks);
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const response = await apiClient.get<ApiResponse<SessionDetail>>(`/sessions/${sessionId}`);
  return response.data.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/sessions/${sessionId}`);
}

// 置顶/取消置顶会话
export async function updateSessionPin(sessionId: string, pinned: boolean): Promise<{session_id: string, pinned: boolean}> {
  const response = await apiClient.patch<ApiResponse<{session_id: string, pinned: boolean}>>(`/sessions/${sessionId}/pin`, { pinned });
  return response.data.data;
}

// 重命名会话
export async function updateSessionTitle(sessionId: string, title: string): Promise<{session_id: string, title: string}> {
  const response = await apiClient.patch<ApiResponse<{session_id: string, title: string}>>(`/sessions/${sessionId}/title`, { title });
  return response.data.data;
}

export function chatWithSession(sessionId: string, data: ChatRequest, callbacks: SSECallbacks<any>): Promise<() => void> {
  return createSSEConnection(`/sessions/${sessionId}/chat`, { method: 'POST', body: data }, callbacks);
}

export async function answerResearchQuestion(
  sessionId: string,
  question: string,
  limit: number = 5,
  modelConfigId?: string | null,
): Promise<ResearchAnswer> {
  const response = await apiClient.post<ApiResponse<ResearchAnswer>>(
    `/sessions/${sessionId}/research/answer`,
    { question, limit, model_config_id: modelConfigId || undefined },
  );
  return response.data.data;
}

export async function getResearchStatus(sessionId: string): Promise<ResearchSessionStatus> {
  const response = await apiClient.get<ApiResponse<ResearchSessionStatus>>(
    `/sessions/${sessionId}/research/status`,
  );
  return response.data.data;
}

export async function createResearchProject(payload: {
  name: string;
  description?: string;
}): Promise<ResearchProject> {
  const response = await apiClient.post<ApiResponse<ResearchProject>>(
    `/sessions/research/projects`,
    payload,
  );
  return response.data.data;
}

export async function listResearchProjects(): Promise<ResearchProject[]> {
  const response = await apiClient.get<ApiResponse<{ projects: ResearchProject[] }>>(
    `/sessions/research/projects`,
  );
  return response.data.data.projects;
}

export async function listResearchProjectPapers(projectId: string): Promise<ResearchProjectPaperAsset[]> {
  const response = await apiClient.get<ApiResponse<{ project_id: string; papers: ResearchProjectPaperAsset[] }>>(
    `/sessions/research/projects/${projectId}/papers`,
  );
  return response.data.data.papers;
}

export async function uploadResearchProjectPaper(
  projectId: string,
  file: File,
): Promise<ResearchProjectPaperUploadResult> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<ApiResponse<ResearchProjectPaperUploadResult>>(
    `/sessions/research/projects/${projectId}/papers`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data.data;
}

export async function promoteChatPaperToLibrary(
  sessionId: string,
  payload: {
    project_id: string;
    sandbox_path: string;
  },
): Promise<ResearchLibraryPromotionResult> {
  const response = await apiClient.post<ApiResponse<ResearchLibraryPromotionResult>>(
    `/sessions/${sessionId}/research/library/promote`,
    payload,
  );
  return response.data.data;
}

export async function setSessionResearchProject(
  sessionId: string,
  projectId: string,
): Promise<SessionResearchProjectBinding> {
  const response = await apiClient.put<ApiResponse<SessionResearchProjectBinding>>(
    `/sessions/${sessionId}/research/project`,
    { project_id: projectId },
  );
  return response.data.data;
}

export async function getSessionResearchProject(sessionId: string): Promise<SessionResearchProjectBinding> {
  const response = await apiClient.get<ApiResponse<SessionResearchProjectBinding>>(
    `/sessions/${sessionId}/research/project`,
  );
  return response.data.data;
}

export async function ingestWebEvidenceSource(
  sessionId: string,
  payload: WebEvidenceIngestPayload,
): Promise<SourceEvidenceIngestResult> {
  const response = await apiClient.post<ApiResponse<SourceEvidenceIngestResult>>(
    `/sessions/${sessionId}/research/web-evidence`,
    payload,
  );
  return response.data.data;
}

export async function ingestDatabaseEvidenceSource(
  sessionId: string,
  payload: DatabaseEvidenceIngestPayload,
): Promise<SourceEvidenceIngestResult> {
  const response = await apiClient.post<ApiResponse<SourceEvidenceIngestResult>>(
    `/sessions/${sessionId}/research/database-evidence`,
    payload,
  );
  return response.data.data;
}

export async function getResearchEvidenceRecord(
  sessionId: string,
  evidenceId: number,
): Promise<ResearchEvidenceRecord> {
  const response = await apiClient.get<ApiResponse<ResearchEvidenceRecord>>(
    `/sessions/${sessionId}/research/evidence/${evidenceId}`,
  );
  return response.data.data;
}

export async function getResearchAuditResult(
  sessionId: string,
  subjectType: 'answer' | 'report',
  subjectId: string,
): Promise<ResearchAudit> {
  const response = await apiClient.get<ApiResponse<ResearchAudit>>(
    `/sessions/${sessionId}/research/audit/${subjectType}/${subjectId}`,
  );
  return response.data.data;
}

export async function listRuntimeResultAudit(
  sessionId: string,
  filters?: RuntimeResultAuditFilters,
): Promise<RuntimeResultAudit> {
  const params = new URLSearchParams();
  if (filters?.tool_pack_id) {
    params.set('tool_pack_id', filters.tool_pack_id);
  }
  if (filters?.result_sha256) {
    params.set('result_sha256', filters.result_sha256);
  }
  const endpoint = `/sessions/${sessionId}/research/runtime-results`;
  const query = params.toString();
  const response = await apiClient.get<ApiResponse<RuntimeResultAudit>>(
    `${endpoint}${query ? `?${query}` : ''}`,
  );
  return response.data.data;
}

export async function exportRuntimeResultAudit(
  sessionId: string,
  filters?: RuntimeResultAuditFilters,
): Promise<RuntimeResultAuditExport> {
  const response = await apiClient.post<ApiResponse<RuntimeResultAuditExport>>(
    `/sessions/${sessionId}/research/runtime-results/export`,
    filters ?? {},
  );
  return response.data.data;
}

export async function promoteResearchMemory(
  sessionId: string,
  payload: {
    subject_type: 'answer' | 'report';
    subject_id: string;
    claim_text: string;
    title?: string;
  },
): Promise<ResearchPromotedMemory> {
  const response = await apiClient.post<ApiResponse<ResearchPromotedMemory>>(
    `/sessions/${sessionId}/research/memory/promote`,
    payload,
  );
  return response.data.data;
}

export async function deleteResearchMemory(
  sessionId: string,
  memoryId: string,
): Promise<ResearchDeletedMemory> {
  const response = await apiClient.delete<ApiResponse<ResearchDeletedMemory>>(
    `/sessions/${sessionId}/research/memory/${encodeURIComponent(memoryId)}`,
  );
  return response.data.data;
}

export async function generateResearchReport(
  sessionId: string,
  question: string,
  limit: number = 8,
): Promise<ResearchReport> {
  const response = await apiClient.post<ApiResponse<ResearchReport>>(
    `/sessions/${sessionId}/research/report`,
    { question, limit },
  );
  return response.data.data;
}

export async function stopSession(sessionId: string): Promise<void> {
  await apiClient.post(`/sessions/${sessionId}/stop`);
}

export async function shareSession(sessionId: string): Promise<{session_id: string, is_shared: boolean}> {
  const response = await apiClient.post<ApiResponse<{session_id: string, is_shared: boolean}>>(`/sessions/${sessionId}/share`);
  return response.data.data;
}

export async function unshareSession(sessionId: string): Promise<{session_id: string, is_shared: boolean}> {
  const response = await apiClient.delete<ApiResponse<{session_id: string, is_shared: boolean}>>(`/sessions/${sessionId}/share`);
  return response.data.data;
}

export async function getSharedSession(sessionId: string): Promise<SessionDetail> {
  const response = await apiClient.get<ApiResponse<SessionDetail>>(`/sessions/shared/${sessionId}`);
  return response.data.data;
}

export async function clearUnreadMessageCount(sessionId: string): Promise<void> {
  await apiClient.post(`/sessions/${sessionId}/clear_unread_message_count`);
}

// Tool Views
export async function viewShellSession(sessionId: string, shellSessionId: string): Promise<any> {
  const response = await apiClient.post<ApiResponse<any>>(`/sessions/${sessionId}/shell`, { session_id: shellSessionId });
  return response.data.data;
}

export async function viewFile(sessionId: string, filePath: string): Promise<{file: string, content: string}> {
  const response = await apiClient.post<ApiResponse<{file: string, content: string}>>(`/sessions/${sessionId}/file`, { file: filePath });
  return response.data.data;
}

export async function getVNCUrl(sessionId: string, expireMinutes: number = 15): Promise<{signed_url: string, expires_in: number}> {
  const response = await apiClient.post<ApiResponse<{signed_url: string, expires_in: number}>>(`/sessions/${sessionId}/vnc/signed-url`, { expire_minutes: expireMinutes });
  return response.data.data;
}

export const getSessionFiles = async (session_id: string): Promise<FileInfo[]> => {
  const response = await apiClient.get<ApiResponse<FileInfo[]>>(`/sessions/${session_id}/files`);
  return response.data.data;
};

export const getSharedSessionFiles = async (session_id: string): Promise<FileInfo[]> => {
  const response = await apiClient.get<ApiResponse<FileInfo[]>>(`/sessions/${session_id}/share/files`);
  return response.data.data;
};

export async function getSkills(): Promise<ExternalSkillItem[]> {
  const response = await apiClient.get<ApiResponse<ExternalSkillItem[]>>('/sessions/skills');
  return response.data.data;
}

export async function blockSkill(skillName: string, blocked: boolean): Promise<{skill_name: string, blocked: boolean}> {
  const response = await apiClient.put<ApiResponse<{skill_name: string, blocked: boolean}>>(`/sessions/skills/${encodeURIComponent(skillName)}/block`, { blocked });
  return response.data.data;
}

export async function deleteSkill(skillName: string): Promise<{skill_name: string, deleted: boolean}> {
  const response = await apiClient.delete<ApiResponse<{skill_name: string, deleted: boolean}>>(`/sessions/skills/${encodeURIComponent(skillName)}`);
  return response.data.data;
}

export async function getSkillFiles(skillName: string, path: string = ""): Promise<any[]> {
  const response = await apiClient.get<ApiResponse<any[]>>(`/sessions/skills/${skillName}/files`, { params: { path } });
  return response.data.data;
}

export async function readSkillFile(skillName: string, file: string): Promise<{file: string, content: string}> {
  const response = await apiClient.post<ApiResponse<{file: string, content: string}>>(`/sessions/skills/${skillName}/read`, { file });
  return response.data.data;
}

export function getSkillFileDownloadUrl(skillName: string, path: string): string {
    // Correct URL for sessions router
    return `/api/v1/sessions/skills/${encodeURIComponent(skillName)}/download?path=${encodeURIComponent(path)}`;
}

export async function saveSkillFromSession(sessionId: string, skillName: string): Promise<{skill_name: string, saved: boolean}> {
  const response = await apiClient.post<ApiResponse<{skill_name: string, saved: boolean}>>(`/sessions/${sessionId}/skills/save`, { skill_name: skillName });
  return response.data.data;
}

// ── External Tools API ──

export async function getTools(): Promise<ExternalToolItem[]> {
  const response = await apiClient.get<ApiResponse<ExternalToolItem[]>>('/sessions/tools');
  return response.data.data;
}

export async function blockTool(toolName: string, blocked: boolean): Promise<{tool_name: string, blocked: boolean}> {
  const response = await apiClient.put<ApiResponse<{tool_name: string, blocked: boolean}>>(`/sessions/tools/${encodeURIComponent(toolName)}/block`, { blocked });
  return response.data.data;
}

export async function deleteTool(toolName: string): Promise<{tool_name: string, deleted: boolean}> {
  const response = await apiClient.delete<ApiResponse<{tool_name: string, deleted: boolean}>>(`/sessions/tools/${encodeURIComponent(toolName)}`);
  return response.data.data;
}

export async function readToolFile(toolName: string): Promise<{file: string, content: string}> {
  const response = await apiClient.post<ApiResponse<{file: string, content: string}>>(`/sessions/tools/${encodeURIComponent(toolName)}/read`);
  return response.data.data;
}

export async function validateToolFromSession(
  sessionId: string,
  toolName: string,
  exampleArgs: Record<string, unknown> = {}
): Promise<{
  tool_name: string,
  status: string,
  checks: string[],
  validated_at: string,
  return_schema?: Record<string, unknown>,
  example_output?: unknown,
  error?: string
}> {
  const response = await apiClient.post<ApiResponse<{
    tool_name: string,
    status: string,
    checks: string[],
    validated_at: string,
    return_schema?: Record<string, unknown>,
    example_output?: unknown,
    error?: string
  }>>(`/sessions/${sessionId}/tools/validate`, {
    tool_name: toolName,
    example_args: exampleArgs,
  });
  return response.data.data;
}

export async function saveToolFromSession(
  sessionId: string,
  toolName: string,
  userConfirmed: boolean,
  replaces?: string,
  toolPack: string = 'literature'
): Promise<{
  tool_name: string,
  saved: boolean,
  replaced?: string,
  tool_pack: { id: string, label: string, research_workflow: string },
  validation: { status: string, checks: string[], validated_at: string, return_schema: Record<string, unknown> }
}> {
  const payload: Record<string, string | boolean> = {
    tool_name: toolName,
    user_confirmed: userConfirmed,
    tool_pack: toolPack,
  };
  if (replaces && replaces !== toolName) {
    payload.replaces = replaces;
  }
  const response = await apiClient.post<ApiResponse<{
    tool_name: string,
    saved: boolean,
    replaced?: string,
    tool_pack: { id: string, label: string, research_workflow: string },
    validation: { status: string, checks: string[], validated_at: string, return_schema: Record<string, unknown> }
  }>>(`/sessions/${sessionId}/tools/save`, payload);
  return response.data.data;
}

export async function readSandboxFile(sessionId: string, path: string): Promise<{file: string, content: string}> {
  const response = await apiClient.get<ApiResponse<{file: string, content: string}>>(`/sessions/${sessionId}/sandbox-file`, { params: { path } });
  return response.data.data;
}

export async function downloadSandboxFile(sessionId: string, path: string): Promise<Blob> {
  const response = await apiClient.get(`/sessions/${sessionId}/sandbox-file/download`, {
    params: { path },
    responseType: 'blob',
  });
  return response.data;
}

export async function optimizePrompt(query: string, modelConfigId?: string | null): Promise<{ optimized_query: string }> {
  const payload: Record<string, string> = { query };
  if (modelConfigId) payload.model_config_id = modelConfigId;
  const response = await apiClient.post<ApiResponse<{ optimized_query: string }>>('/science/optimize_prompt', payload);
  return response.data.data;
}
