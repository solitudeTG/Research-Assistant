<template>
  <div class="flex h-full w-full min-w-0 flex-col overflow-hidden bg-[var(--background-gray-main)]">
    <div class="flex h-14 flex-shrink-0 items-center justify-between border-b border-[var(--border-light)] bg-[var(--background-white-main)] px-5">
      <div class="min-w-0">
        <h1 class="truncate text-base font-semibold text-[var(--text-primary)]">研究智能体</h1>
        <p class="mt-0.5 text-xs text-[var(--text-tertiary)]">
          受治理的科研 subagent 配置，供 Supervisor 在证据审计和范围化阅读任务中按需调度。
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
      <aside class="flex w-[340px] flex-shrink-0 flex-col border-r border-[var(--border-light)] bg-[var(--background-white-main)]">
        <div class="border-b border-[var(--border-light)] px-3 py-2">
          <div class="flex items-center justify-between text-[11px] text-[var(--text-tertiary)]">
            <span>已注册 subagent</span>
            <span class="tabular-nums">{{ agents.length }}</span>
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto p-2">
          <button
            v-for="agent in agents"
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
            <div class="mt-1 flex items-center gap-2 text-[10px] text-[var(--text-tertiary)]">
              <span class="font-mono">{{ agent.name }}</span>
              <span>v{{ agent.version }}</span>
              <span>{{ validationStatusLabel(agent.validation_status) }}</span>
            </div>
            <p class="mt-1 line-clamp-2 text-xs opacity-75">{{ displayAgentDescription(agent) }}</p>
          </button>

          <div v-if="!agents.length && !loading" class="px-3 py-8 text-center text-xs text-[var(--text-tertiary)]">
            暂无已启用的受治理研究智能体。
          </div>
        </div>
      </aside>

      <main class="min-w-0 flex-1 overflow-auto">
        <div v-if="selectedAgent" class="mx-auto flex max-w-[1280px] flex-col gap-4 p-5">
          <section class="border-b border-[var(--border-light)] pb-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <ShieldCheck v-if="selectedAgent.name === 'research_auditor'" :size="18" class="text-blue-500" />
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
                  {{ selectedAgent.output_boundary }}
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

          <section class="grid grid-cols-1 gap-3 xl:grid-cols-3">
            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] p-3">
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">边界</h3>
                <span class="text-[10px] text-[var(--text-tertiary)]">F020</span>
              </div>
              <dl class="space-y-2 text-xs">
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">可直接回复用户</dt>
                  <dd class="text-[var(--text-primary)]">{{ booleanLabel(selectedAgent.can_answer_user) }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">可写入产物</dt>
                  <dd class="text-[var(--text-primary)]">{{ booleanLabel(selectedAgent.can_write_artifacts) }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--text-tertiary)]">输出边界</dt>
                  <dd class="font-mono text-[var(--text-primary)]">{{ selectedAgent.output_boundary }}</dd>
                </div>
              </dl>
              <div class="mt-3 border-t border-[var(--border-light)] pt-2">
                <div class="mb-1 text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">允许输出</div>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="boundary in governedOutputBoundaries"
                    :key="boundary"
                    class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]"
                  >
                    {{ boundary }}
                  </span>
                </div>
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
              </div>
            </div>

            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] p-3">
              <div class="mb-2 flex items-center justify-between">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">技能</h3>
                <span class="text-[10px] tabular-nums text-[var(--text-tertiary)]">{{ selectedAgent.skill_refs.length }}</span>
              </div>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="skill in selectedAgent.skill_refs"
                  :key="skill"
                  class="rounded-md bg-[var(--fill-tsp-gray-main)] px-2 py-1 font-mono text-[11px] text-[var(--text-secondary)]"
                >
                  {{ skill }}
                </span>
              </div>
            </div>
          </section>

          <section class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)]">
              <div class="border-b border-[var(--border-light)] px-3 py-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">系统提示词</h3>
              </div>
              <pre class="max-h-[360px] overflow-auto whitespace-pre-wrap px-3 py-3 text-xs leading-5 text-[var(--text-secondary)]">{{ selectedAgent.system_prompt }}</pre>
            </div>

            <div class="rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)]">
              <div class="border-b border-[var(--border-light)] px-3 py-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">输入边界</h3>
              </div>
              <pre class="max-h-[360px] overflow-auto whitespace-pre-wrap px-3 py-3 text-xs leading-5 text-[var(--text-secondary)]">{{ formattedInputBoundaries }}</pre>
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
import { computed, onMounted, ref } from 'vue';
import { BookOpenCheck, RefreshCw, ShieldCheck } from 'lucide-vue-next';
import { listResearchAgents, type ResearchAgentDefinition } from '../api/agent';

const agents = ref<ResearchAgentDefinition[]>([]);
const selectedAgentName = ref('');
const loading = ref(false);
const preferredAgentOrder = ['research_auditor', 'paper_reader_worker'];
const governedOutputBoundaries = ['context_only', 'process_trace'];
const builtinAgentCopy: Record<string, { displayName: string; description: string }> = {
  research_auditor: {
    displayName: '审计智能体',
    description: '审查草稿结论与引用证据之间的匹配关系，只返回过程审计结果，不写最终回答。',
  },
  paper_reader_worker: {
    displayName: '阅读 Worker',
    description: '读取 Supervisor 指定的材料包，用于多论文批量阅读或追问中的聚焦重读，并返回 context-only 笔记。',
  },
};

const selectedAgent = computed(() => agents.value.find(agent => agent.name === selectedAgentName.value) || agents.value[0] || null);

const formattedInputBoundaries = computed(() => {
  if (!selectedAgent.value) return '';
  return JSON.stringify(selectedAgent.value.input_boundaries, null, 2);
});

const displayAgentName = (agent: ResearchAgentDefinition) => (
  builtinAgentCopy[agent.name]?.displayName || agent.display_name
);

const displayAgentDescription = (agent: ResearchAgentDefinition) => (
  builtinAgentCopy[agent.name]?.description || agent.description
);

const booleanLabel = (value: boolean) => (value ? '是' : '否');

const validationStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    valid: '已验证',
    invalid: '未通过',
    draft: '草稿',
  };
  return labels[status] || status;
};

const refreshAgents = async () => {
  loading.value = true;
  try {
    const loadedAgents = await listResearchAgents();
    agents.value = loadedAgents.sort((left, right) => {
      const leftIndex = preferredAgentOrder.indexOf(left.name);
      const rightIndex = preferredAgentOrder.indexOf(right.name);
      const normalizedLeft = leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex;
      const normalizedRight = rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex;
      return normalizedLeft - normalizedRight || left.display_name.localeCompare(right.display_name);
    });
    if (!agents.value.some(agent => agent.name === selectedAgentName.value)) {
      selectedAgentName.value = agents.value[0]?.name || '';
    }
  } finally {
    loading.value = false;
  }
};

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
