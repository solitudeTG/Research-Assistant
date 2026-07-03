<template>
  <div class="flex h-full w-full min-w-0 flex-col overflow-hidden bg-[var(--background-gray-main)]">
    <div class="flex h-14 flex-shrink-0 items-center justify-between border-b border-[var(--border-light)] bg-[var(--background-white-main)] px-5">
      <div class="min-w-0">
        <h1 class="truncate text-base font-semibold text-[var(--text-primary)]">研究智能体</h1>
        <p class="mt-0.5 text-xs text-[var(--text-tertiary)]">
          管理 Supervisor 可委派的研究 subagent；系统内置 Agent 只读展示，用户自定义 Agent 才允许治理和验证。
        </p>
      </div>
      <button
        class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] px-2.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="loading"
        @click="refreshAgents"
      >
        <RefreshCw :size="14" :class="{ 'animate-spin': loading }" />
        刷新
      </button>
    </div>

    <div class="flex min-h-0 flex-1">
      <aside class="flex w-[360px] flex-shrink-0 flex-col border-r border-[var(--border-light)] bg-[var(--background-white-main)]">
        <div class="border-b border-[var(--border-light)] px-3 py-2">
          <div class="flex items-center justify-between text-[11px] text-[var(--text-tertiary)]">
            <span>已注册 Agent</span>
            <span class="tabular-nums">{{ agents.length }}</span>
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto p-2">
          <button
            v-for="agent in orderedAgents"
            :key="agent.name"
            class="mb-1 w-full rounded-md border px-3 py-2 text-left transition-colors"
            :class="selectedAgentName === agent.name
              ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-300'
              : 'border-transparent text-[var(--text-secondary)] hover:border-[var(--border-light)] hover:bg-gray-50 dark:hover:bg-white/5'"
            @click="selectedAgentName = agent.name"
          >
            <div class="flex min-w-0 items-center justify-between gap-2">
              <span class="truncate text-sm font-medium">{{ displayAgentName(agent) }}</span>
              <span
                class="rounded px-1.5 py-0.5 text-[10px] font-medium"
                :class="agent.enabled ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'"
              >
                {{ agent.enabled ? '已启用' : '已停用' }}
              </span>
            </div>
            <div class="mt-1 flex min-w-0 flex-wrap items-center gap-1.5 text-[10px] text-[var(--text-tertiary)]">
              <span class="font-mono">{{ agent.name }}</span>
              <span class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5">{{ agentTypeLabel(agent) }}</span>
              <span class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5">{{ editabilityLabel(agent) }}</span>
              <span>{{ validationStatusLabel(agent.validation_status) }}</span>
            </div>
            <p class="mt-1 line-clamp-2 text-xs opacity-75">{{ displayAgentDescription(agent) }}</p>
          </button>

          <div v-if="!agents.length && !loading" class="px-3 py-8 text-center text-xs text-[var(--text-tertiary)]">
            暂无已注册的研究智能体。
          </div>
        </div>
      </aside>

      <main class="min-w-0 flex-1 overflow-auto">
        <div v-if="selectedAgent" class="mx-auto flex max-w-[1280px] flex-col gap-4 p-5">
          <section class="border-b border-[var(--border-light)] pb-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <Cpu v-if="selectedAgent.agent_type === 'system_builtin'" :size="18" class="text-slate-500" />
                  <ShieldCheck v-else-if="selectedAgent.name === 'research_auditor'" :size="18" class="text-blue-500" />
                  <BookOpenCheck v-else :size="18" class="text-emerald-500" />
                  <h2 class="truncate text-base font-semibold text-[var(--text-primary)]">
                    {{ displayAgentName(selectedAgent) }}
                  </h2>
                </div>
                <p class="mt-1 max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
                  {{ displayAgentDescription(selectedAgent) }}
                </p>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="rounded-md bg-[var(--fill-tsp-gray-main)] px-2 py-1 text-[11px] font-medium text-[var(--text-secondary)]">
                  {{ agentTypeLabel(selectedAgent) }}
                </span>
                <span class="rounded-md bg-[var(--fill-tsp-gray-main)] px-2 py-1 text-[11px] font-medium text-[var(--text-secondary)]">
                  {{ editabilityLabel(selectedAgent) }}
                </span>
                <span
                  class="rounded-md px-2 py-1 text-[11px] font-medium"
                  :class="selectedAgent.citation_evidence ? 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300' : 'bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300'"
                >
                  citation_evidence={{ selectedAgent.citation_evidence }}
                </span>
              </div>
            </div>
          </section>

          <section class="grid grid-cols-1 gap-3 xl:grid-cols-4">
            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] p-3">
              <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Registry</h3>
              <dl class="space-y-2 text-xs">
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">类型</dt>
                  <dd class="font-mono text-[var(--text-primary)]">{{ selectedAgent.agent_type }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">来源</dt>
                  <dd class="font-mono text-[var(--text-primary)]">{{ selectedAgent.source }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">editable</dt>
                  <dd class="text-[var(--text-primary)]">{{ booleanLabel(selectedAgent.editable) }}</dd>
                </div>
              </dl>
            </div>

            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] p-3">
              <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">边界</h3>
              <dl class="space-y-2 text-xs">
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">直接回复用户</dt>
                  <dd class="text-[var(--text-primary)]">{{ booleanLabel(selectedAgent.can_answer_user) }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">写入产物</dt>
                  <dd class="text-[var(--text-primary)]">{{ booleanLabel(selectedAgent.can_write_artifacts) }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">输出边界</dt>
                  <dd class="font-mono text-[var(--text-primary)]">{{ selectedAgent.output_boundary }}</dd>
                </div>
              </dl>
              <div class="mt-3 flex flex-wrap gap-1 border-t border-[var(--border-light)] pt-2">
                <span
                  v-for="boundary in governedOutputBoundaries"
                  :key="boundary"
                  class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]"
                >
                  {{ boundary }}
                </span>
              </div>
            </div>

            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] p-3">
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">工具</h3>
                <span class="text-[10px] tabular-nums text-[var(--text-tertiary)]">{{ selectedAgent.allowed_tools.length }}</span>
              </div>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="tool in selectedAgent.allowed_tools"
                  :key="tool"
                  class="rounded-md bg-[var(--fill-tsp-gray-main)] px-2 py-1 font-mono text-[11px] text-[var(--text-secondary)]"
                >
                  {{ tool }}
                </span>
                <span v-if="!selectedAgent.allowed_tools.length" class="text-xs text-[var(--text-tertiary)]">无挂载工具</span>
              </div>
            </div>

            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] p-3">
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">治理动作</h3>
                <Lock v-if="!selectedAgent.editable" :size="13" class="text-[var(--text-tertiary)]" />
              </div>
              <div class="flex flex-wrap gap-2">
                <button class="h-7 rounded-md border border-[var(--border-light)] px-2 text-xs text-[var(--text-secondary)] disabled:cursor-not-allowed disabled:opacity-50" :disabled="!selectedAgent.editable">编辑</button>
                <button class="h-7 rounded-md border border-[var(--border-light)] px-2 text-xs text-[var(--text-secondary)] disabled:cursor-not-allowed disabled:opacity-50" :disabled="!selectedAgent.editable">启停</button>
                <button
                  class="h-7 rounded-md border border-[var(--border-light)] px-2 text-xs text-[var(--text-secondary)] disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="!selectedAgent.editable || validatingAgentName === selectedAgent.name"
                  @click="runValidation(selectedAgent)"
                >
                  {{ validatingAgentName === selectedAgent.name ? '验证中' : '运行验证' }}
                </button>
              </div>
            </div>
          </section>

          <section class="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)]">
              <div class="flex items-center justify-between border-b border-[var(--border-light)] px-3 py-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">最近运行</h3>
                <History :size="14" class="text-[var(--text-tertiary)]" />
              </div>
              <div class="divide-y divide-[var(--border-light)]">
                <div
                  v-for="run in selectedAgentRuns"
                  :key="run.task_id"
                  class="px-3 py-2 text-xs"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span class="font-mono text-[var(--text-primary)]">{{ run.task_id }}</span>
                    <span class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5 text-[10px] text-[var(--text-secondary)]">{{ run.status }}</span>
                  </div>
                  <div class="mt-1 flex flex-wrap gap-2 text-[10px] text-[var(--text-tertiary)]">
                    <span>{{ formatRunTime(run.completed_at || run.started_at) }}</span>
                    <span class="font-mono">{{ run.output_boundary }}</span>
                    <span>citation_evidence={{ run.citation_evidence }}</span>
                  </div>
                </div>
                <div v-if="!selectedAgentRuns.length" class="px-3 py-5 text-xs text-[var(--text-tertiary)]">
                  暂无真实运行记录
                </div>
              </div>
            </div>

            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)]">
              <div class="flex items-center justify-between border-b border-[var(--border-light)] px-3 py-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">验证示例</h3>
                <CheckCircle2 v-if="selectedValidation?.status === 'passed'" :size="14" class="text-emerald-500" />
                <AlertCircle v-else :size="14" class="text-[var(--text-tertiary)]" />
              </div>
              <div class="px-3 py-3 text-xs">
                <template v-if="selectedValidation">
                  <div class="mb-2 flex items-center justify-between">
                    <span class="text-[var(--text-tertiary)]">状态</span>
                    <span class="font-medium text-[var(--text-primary)]">{{ selectedValidation.status }}</span>
                  </div>
                  <div class="mb-2 flex flex-wrap gap-1.5">
                    <span
                      v-for="check in selectedValidation.checks"
                      :key="check"
                      class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]"
                    >
                      {{ check }}
                    </span>
                  </div>
                  <pre v-if="selectedValidation.errors.length" class="max-h-28 overflow-auto whitespace-pre-wrap rounded bg-red-50 p-2 text-[11px] text-red-700 dark:bg-red-950/30 dark:text-red-300">{{ selectedValidation.errors.join('\n') }}</pre>
                  <pre v-else class="max-h-28 overflow-auto whitespace-pre-wrap rounded bg-[var(--fill-tsp-gray-main)] p-2 text-[11px] text-[var(--text-secondary)]">{{ formatValidationPreview(selectedValidation.example_result) }}</pre>
                </template>
                <div v-else class="text-[var(--text-tertiary)]">
                  {{ selectedAgent.editable ? '运行验证以检查 minimal envelope 与证据边界。' : '系统内置 Agent 由 runtime 管理，无需自定义验证。' }}
                </div>
              </div>
            </div>
          </section>

          <section class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)]">
              <div class="border-b border-[var(--border-light)] px-3 py-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">系统提示词</h3>
              </div>
              <pre class="max-h-[360px] overflow-auto whitespace-pre-wrap px-3 py-3 text-xs leading-5 text-[var(--text-secondary)]">{{ selectedAgent.system_prompt || '系统内置 Agent 由 DeepAgents runtime 管理，不在本 Registry 中编辑 system_prompt。' }}</pre>
            </div>

            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)]">
              <div class="border-b border-[var(--border-light)] px-3 py-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">输入边界与 metadata</h3>
              </div>
              <pre class="max-h-[360px] overflow-auto whitespace-pre-wrap px-3 py-3 text-xs leading-5 text-[var(--text-secondary)]">{{ formattedGovernance }}</pre>
            </div>
          </section>
        </div>

        <div v-else class="flex h-full items-center justify-center text-sm text-[var(--text-tertiary)]">
          {{ loading ? '正在加载研究智能体...' : '暂无已注册研究智能体。' }}
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { AlertCircle, BookOpenCheck, CheckCircle2, Cpu, History, Lock, RefreshCw, ShieldCheck } from 'lucide-vue-next';
import {
  listResearchAgentRuns,
  listResearchAgents,
  validateResearchAgent,
  type ResearchAgentDefinition,
  type ResearchAgentRun,
  type ResearchAgentValidationResult,
} from '../api/agent';

const agents = ref<ResearchAgentDefinition[]>([]);
const selectedAgentName = ref('');
const loading = ref(false);
const loadingRunsAgentName = ref('');
const validatingAgentName = ref('');
const recentRuns = ref<Record<string, ResearchAgentRun[]>>({});
const validationResults = ref<Record<string, ResearchAgentValidationResult>>({});
const preferredAgentOrder = ['general-purpose', 'research_auditor', 'paper_reader_worker'];
const governedOutputBoundaries = ['context_only', 'process_trace'];

const agentCopy: Record<string, { displayName: string; description: string }> = {
  'general-purpose': {
    displayName: '通用执行 Agent',
    description: 'DeepAgents 默认携带的系统内置 Agent。它属于过程 trace，不写 citation evidence，也不允许在 Registry 中编辑。',
  },
  research_auditor: {
    displayName: '审计智能体',
    description: '审查草稿结论与引用证据之间的匹配关系，只返回过程审计结果，不写最终回答。',
  },
  paper_reader_worker: {
    displayName: '阅读 Worker',
    description: '读取 Supervisor 指定的材料包，用于多论文批量阅读或追问中的聚焦重读，并返回 context-only 笔记。',
  },
};

const orderedAgents = computed(() => [...agents.value].sort((left, right) => {
  const leftIndex = preferredAgentOrder.indexOf(left.name);
  const rightIndex = preferredAgentOrder.indexOf(right.name);
  const normalizedLeft = leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex;
  const normalizedRight = rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex;
  return normalizedLeft - normalizedRight || left.display_name.localeCompare(right.display_name);
}));

const selectedAgent = computed(() => agents.value.find(agent => agent.name === selectedAgentName.value) || orderedAgents.value[0] || null);
const selectedAgentRuns = computed(() => selectedAgent.value ? (recentRuns.value[selectedAgent.value.name] || []) : []);
const selectedValidation = computed(() => selectedAgent.value ? validationResults.value[selectedAgent.value.name] : null);

const formattedGovernance = computed(() => {
  if (!selectedAgent.value) return '';
  return JSON.stringify({
    input_boundaries: selectedAgent.value.input_boundaries,
    metadata: selectedAgent.value.metadata,
  }, null, 2);
});

const displayAgentName = (agent: ResearchAgentDefinition) => (
  agentCopy[agent.name]?.displayName || agent.display_name
);

const displayAgentDescription = (agent: ResearchAgentDefinition) => (
  agentCopy[agent.name]?.description || agent.description
);

const agentTypeLabel = (agent: ResearchAgentDefinition) => (
  agent.agent_type === 'system_builtin' ? '系统内置' : (agent.agent_type === 'custom' ? '用户自定义' : agent.agent_type)
);

const editabilityLabel = (agent: ResearchAgentDefinition) => (
  agent.editable ? '可编辑' : '只读'
);

const booleanLabel = (value: boolean) => (value ? '是' : '否');

const validationStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    valid: '已验证',
    invalid: '未通过',
    draft: '草稿',
    system_managed: '系统托管',
  };
  return labels[status] || status;
};

const formatRunTime = (value?: string | null) => {
  if (!value) return '时间未知';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const formatValidationPreview = (value: unknown) => {
  if (value === undefined || value === null) return '无示例输出';
  return JSON.stringify(value, null, 2);
};

const loadAgentRuns = async (agentName: string) => {
  loadingRunsAgentName.value = agentName;
  try {
    recentRuns.value = {
      ...recentRuns.value,
      [agentName]: await listResearchAgentRuns(agentName, 5),
    };
  } finally {
    if (loadingRunsAgentName.value === agentName) {
      loadingRunsAgentName.value = '';
    }
  }
};

const runValidation = async (agentToValidate: ResearchAgentDefinition) => {
  if (!agentToValidate.editable) return;
  validatingAgentName.value = agentToValidate.name;
  try {
    validationResults.value = {
      ...validationResults.value,
      [agentToValidate.name]: await validateResearchAgent(agentToValidate.name),
    };
  } finally {
    if (validatingAgentName.value === agentToValidate.name) {
      validatingAgentName.value = '';
    }
  }
};

const refreshAgents = async () => {
  loading.value = true;
  try {
    agents.value = await listResearchAgents();
    if (!agents.value.some(agent => agent.name === selectedAgentName.value)) {
      selectedAgentName.value = orderedAgents.value[0]?.name || '';
    }
  } finally {
    loading.value = false;
  }
};

watch(
  () => selectedAgent.value?.name,
  (agentName) => {
    if (agentName) {
      void loadAgentRuns(agentName);
    }
  },
);

onMounted(refreshAgents);
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
