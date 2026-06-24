import type { FileInfo } from '../api/file';

export type AgentSSEEvent = {
  event: 'tool' | 'step' | 'message' | 'message_chunk' | 'message_chunk_done' | 'error' | 'done' | 'title' | 'wait' | 'plan' | 'attachments' | 'thinking' | 'skill_save_prompt' | 'tool_save_prompt';
  data: ToolEventData | StepEventData | MessageEventData | MessageChunkEventData | MessageChunkDoneEventData | ErrorEventData | DoneEventData | TitleEventData | WaitEventData | PlanEventData | ThinkingEventData | SkillSavePromptEventData | ToolSavePromptEventData;
}

export interface BaseEventData {
  event_id: string;
  timestamp: number;
}

/** 工具元数据（图标、分类、描述） */
export interface ToolMetaData {
  icon: string;
  category: string;
  description: string;
  sandbox?: boolean;
}

export interface ResearchToolPackMetadata {
  id: string;
  label: string;
  research_workflow?: string;
}

export interface ToolResultContract {
  kind: string;
  schema: Record<string, any>;
  example_preview?: any;
  truncated?: boolean;
}

export interface ToolRuntimeResultSummary {
  kind: string;
  preview?: any;
  result_sha256: string;
  truncated?: boolean;
  result_contract?: ToolResultContract;
  tool_pack?: ResearchToolPackMetadata;
  context_boundary: 'process_trace';
  citation_evidence: false;
}

export interface ToolEventData extends BaseEventData {
  tool_call_id: string;
  name: string;
  status: "calling" | "called";
  function: string;
  args: {[key: string]: any};
  content?: any;
  /** 工具调用耗时（毫秒），仅 status=called 时存在 */
  duration_ms?: number;
  /** 工具元数据（图标、分类、描述） */
  tool_meta?: ToolMetaData;
  result_contract?: ToolResultContract;
  tool_pack?: ResearchToolPackMetadata;
  runtime_result_summary?: ToolRuntimeResultSummary;
}

export interface StepEventData extends BaseEventData {
  status: "pending" | "running" | "in_progress" | "completed" | "failed"
  id: string
  description: string
  tools?: ToolEventData[]
}

export interface MessageChunkEventData extends BaseEventData {
  content: string;
}

export interface MessageChunkDoneEventData extends BaseEventData {
}

export interface MessageEventData extends BaseEventData {
  content: string;
  role: "user" | "assistant";
  attachments: FileInfo[];
  metadata?: Record<string, any>;
}

export interface ErrorEventData extends BaseEventData {
  error: string;
}

/** 统计信息 */
export interface StatisticsData {
  total_duration_ms?: number;
  tool_call_count?: number;
  input_tokens?: number;
  output_tokens?: number;
  token_count?: number;
}

/** 轮次文件信息（done 事件中携带） */
export interface RoundFileInfo {
  file_id: string;
  filename: string;
  relative_path: string;
  size: number;
  upload_date: string;
  file_url: string;
  category: 'output' | 'research_data';
}

export interface DoneEventData extends BaseEventData {
  /** 执行统计信息 */
  statistics?: StatisticsData;
  /** 本轮新增/修改的文件列表 */
  round_files?: RoundFileInfo[];
}

export interface WaitEventData extends BaseEventData {
}

export interface TitleEventData extends BaseEventData {
  title: string;
}

export interface PlanEventData extends BaseEventData {
  steps: StepEventData[];
}

/** 思考过程事件 */
export interface ThinkingEventData extends BaseEventData {
  content: string;
}

export interface SkillSavePromptEventData extends BaseEventData {
  skill_name?: string;
}

export interface ToolSavePromptEventData extends BaseEventData {
  tool_name?: string;
  replaces?: string | null;
}
