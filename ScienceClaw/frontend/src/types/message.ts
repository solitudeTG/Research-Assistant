import type { FileInfo } from '../api/file';
import type { ToolMetaData, StatisticsData, RoundFileInfo } from './event';

export type MessageType = "user" | "assistant" | "tool" | "step" | "attachments" | "thinking";

export interface Message {
  type: MessageType;
  content: BaseContent;
}

export interface BaseContent {
  timestamp: number;
}

export interface MessageContent extends BaseContent {
  content: string;
  metadata?: {
    research_assistant?: ResearchAnswerMetadata;
    [key: string]: any;
  };
  /** 该轮对话的统计信息 */
  statistics?: StatisticsData;
  /** 本轮新增/修改的文件列表 */
  round_files?: RoundFileInfo[];
}

export interface ResearchCitationMetadata {
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
}

export interface ResearchContextMemoryMetadata {
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

export interface ResearchAuditClaimMetadata {
  claim_text: string;
  status: 'approved' | 'unsupported' | 'invalid_source';
  evidence_ids: number[];
  notes: string[];
  support_score?: number;
}

export interface ResearchAuditMetadata {
  status: 'approved' | 'partial' | 'unsupported' | 'invalid_source';
  claim_count: number;
  approved_claim_count: number;
  unsupported_claim_count: number;
  invalid_source_count: number;
  boundaries: {
    citation_evidence: string[];
    context_only: string[];
  };
  claims: ResearchAuditClaimMetadata[];
}

export interface ResearchAnswerMetadata {
  answer_id?: string;
  content?: string;
  question?: string;
  citations?: ResearchCitationMetadata[];
  citation_count?: number;
  context_memory?: ResearchContextMemoryMetadata[];
  context_memory_count?: number;
  audit?: ResearchAuditMetadata;
  report?: {
    report_id: string;
    title: string;
    question: string;
    markdown_path: string;
    evidence_map_path: string;
    citation_count: number;
  };
}

export interface ToolContent extends BaseContent {
  tool_call_id: string;
  name: string;
  function: string;
  args: any;
  content?: any;
  status: "calling" | "called";
  /** 工具调用耗时（毫秒） */
  duration_ms?: number;
  /** 工具元数据（图标、分类、描述） */
  tool_meta?: ToolMetaData;
}

export interface StepContent extends BaseContent {
  id: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  tools: ToolContent[];
}

export interface AttachmentsContent extends BaseContent {
  role: "user" | "assistant";
  attachments: FileInfo[];
}

export interface ThinkingContent extends BaseContent {
  content: string;
}
