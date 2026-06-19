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
  source_type: 'paper';
}

export interface ResearchAnswerMetadata {
  content?: string;
  question?: string;
  citations?: ResearchCitationMetadata[];
  citation_count?: number;
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
