<template>
  <div class="flex h-full w-full min-w-0 flex-col overflow-hidden bg-[var(--background-gray-main)]">
    <header class="flex h-14 flex-shrink-0 items-center justify-between border-b border-[var(--border-light)] bg-[var(--background-white-main)] px-5" data-page="Research Agents">
      <div class="min-w-0">
        <h1 class="truncate text-base font-semibold text-[var(--text-primary)]">研究智能体</h1>
        <p class="mt-0.5 truncate text-xs text-[var(--text-tertiary)]">
          管理 Supervisor 可委派的研究 subagent；用户只配置身份、委派方式和能力权限。
        </p>
      </div>
      <button
        class="inline-flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-light)] bg-[var(--background-white-main)] px-2.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="loading"
        title="刷新 Research Agents"
        @click="refreshAgents"
      >
        <RefreshCw :size="14" :class="{ 'animate-spin': loading }" />
        刷新
      </button>
    </header>

    <div class="flex min-h-0 flex-1">
      <aside class="flex w-[340px] flex-shrink-0 flex-col border-r border-[var(--border-light)] bg-[var(--background-white-main)]">
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
            class="mb-1 grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-2 rounded-md border px-3 py-2 text-left transition-colors"
            :class="selectedAgentName === agent.name
              ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-300'
              : 'border-transparent text-[var(--text-secondary)] hover:border-[var(--border-light)] hover:bg-gray-50 dark:hover:bg-white/5'"
            @click="selectAgent(agent.name)"
          >
            <div class="min-w-0">
              <div class="flex min-w-0 items-center gap-2">
                <span class="truncate text-sm font-medium">{{ displayAgentName(agent) }}</span>
                <span class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5 text-[10px] text-[var(--text-tertiary)]">{{ agentTypeLabel(agent) }}</span>
              </div>
              <div class="mt-1 flex min-w-0 flex-wrap items-center gap-1.5 text-[10px] text-[var(--text-tertiary)]">
                <span class="font-mono">{{ agent.name }}</span>
                <span>{{ validationStatusLabel(agent.validation_status) }}</span>
                <span>v{{ agent.version }}</span>
              </div>
            </div>
            <span
              class="h-5 rounded px-1.5 py-0.5 text-[10px] font-medium"
              :class="agent.enabled ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'"
            >
              {{ agent.enabled ? '已启动' : '已暂停' }}
            </span>
          </button>

          <div v-if="!agents.length && !loading" class="px-3 py-8 text-center text-xs text-[var(--text-tertiary)]">
            暂无已注册的研究智能体。
          </div>
        </div>
      </aside>

      <main class="min-w-0 flex-1 overflow-auto">
        <div
          v-if="selectedAgent"
          class="mx-auto grid max-w-[1360px] grid-cols-1 gap-4 p-5"
          :class="sidePanelExpanded ? 'xl:grid-cols-[minmax(0,1fr)_340px]' : 'xl:grid-cols-1'"
        >
          <section class="min-w-0">
            <div class="border-b border-[var(--border-light)] pb-3">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <Cpu v-if="selectedAgent.agent_type === 'system_builtin'" :size="18" class="text-slate-500" />
                    <ShieldCheck v-else-if="selectedAgent.name === 'research_auditor'" :size="18" class="text-blue-500" />
                    <BookOpenCheck v-else :size="18" class="text-emerald-500" />
                    <h2 class="truncate text-base font-semibold text-[var(--text-primary)]">{{ displayAgentName(selectedAgent) }}</h2>
                  </div>
                  <p class="mt-1 max-w-4xl text-sm leading-6 text-[var(--text-secondary)]">{{ displayAgentDescription(selectedAgent) }}</p>
                </div>
                <div class="flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span class="rounded bg-[var(--fill-tsp-gray-main)] px-2 py-1 text-[var(--text-secondary)]">{{ agentTypeLabel(selectedAgent) }}</span>
                  <span class="rounded bg-[var(--fill-tsp-gray-main)] px-2 py-1 text-[var(--text-secondary)]">{{ editabilityLabel(selectedAgent) }}</span>
                  <span class="rounded bg-blue-50 px-2 py-1 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">不作为引用证据</span>
                </div>
              </div>

              <div class="mt-3 flex flex-wrap items-center gap-2">
                <button
                  class="inline-flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-light)] px-2.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="!selectedAgent.editable"
                  title="编辑自定义 Agent 草稿"
                  @click="startEditing(selectedAgent)"
                >
                  <Pencil :size="14" />
                  编辑
                </button>
                <button
                  class="inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-50"
                  :class="selectedAgent.enabled
                    ? 'border-[var(--border-light)] text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)]'
                    : 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300'"
                  :disabled="!selectedAgent.editable || savingAgentName === selectedAgent.name || validatingAgentName === selectedAgent.name"
                  title="启动前会自动运行发布验证"
                  @click="toggleAgentAvailability(selectedAgent)"
                >
                  <component :is="selectedAgent.enabled ? PauseCircle : Power" :size="14" />
                  {{ availabilityActionLabel(selectedAgent) }}
                </button>
                <button
                  class="inline-flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-light)] px-2.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)]"
                  @click="sidePanelExpanded = !sidePanelExpanded"
                >
                  <PanelRight :size="14" />
                  {{ sidePanelExpanded ? '隐藏验证与运行' : '查看验证与运行' }}
                </button>
              </div>
            </div>

            <div class="mt-4 grid gap-3 md:grid-cols-3">
              <div class="border-b border-[var(--border-light)] pb-2 md:border-b-0" data-section="BaseInfo">
                <div class="text-[11px] text-[var(--text-tertiary)]">运行状态</div>
                <div class="mt-1 text-sm font-medium text-[var(--text-primary)]">{{ selectedAgent.enabled ? '已启动' : '已暂停' }}</div>
              </div>
              <div class="border-b border-[var(--border-light)] pb-2 md:border-b-0">
                <div class="text-[11px] text-[var(--text-tertiary)]">发布状态</div>
                <div class="mt-1 text-sm font-medium text-[var(--text-primary)]">{{ validationStatusLabel(selectedAgent.validation_status) }}</div>
              </div>
              <div>
                <div class="text-[11px] text-[var(--text-tertiary)]">版本</div>
                <div class="mt-1 font-mono text-sm text-[var(--text-primary)]">v{{ selectedAgent.version }}</div>
              </div>
            </div>

            <div v-if="selectedAgent.editable" class="mt-4 space-y-4">
              <section class="border border-[var(--border-light)] bg-[var(--background-white-main)]" data-section="BaseInfo">
                <div class="flex items-center justify-between border-b border-[var(--border-light)] px-3 py-2">
                  <h3 class="text-xs font-semibold uppercase text-[var(--text-tertiary)]">基础信息</h3>
                  <div class="flex items-center gap-2">
                    <button
                      class="h-7 rounded-md border border-[var(--border-light)] px-2 text-xs text-[var(--text-secondary)] disabled:cursor-not-allowed disabled:opacity-50"
                      :disabled="savingAgentName === selectedAgent.name"
                      @click="resetDraft(selectedAgent)"
                    >
                      重置
                    </button>
                    <button
                      class="h-7 rounded-md bg-blue-600 px-2.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                      :disabled="savingAgentName === selectedAgent.name"
                      @click="saveAgentEdits(selectedAgent)"
                    >
                      {{ savingAgentName === selectedAgent.name ? '保存中' : '保存草稿' }}
                    </button>
                  </div>
                </div>

                <div class="grid gap-3 p-3 text-xs">
                  <label class="flex flex-col gap-1">
                    <span class="text-[var(--text-tertiary)]">显示名称</span>
                    <input v-model="editDraft.display_name" class="h-8 rounded-md border border-[var(--border-light)] bg-transparent px-2 text-[var(--text-primary)]" />
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[var(--text-tertiary)]">何时委派</span>
                    <textarea v-model="editDraft.description" rows="3" class="rounded-md border border-[var(--border-light)] bg-transparent px-2 py-1.5 text-[var(--text-primary)]" />
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[var(--text-tertiary)]">System prompt</span>
                    <textarea v-model="editDraft.system_prompt" rows="7" class="rounded-md border border-[var(--border-light)] bg-transparent px-2 py-1.5 font-mono text-[var(--text-primary)]" />
                  </label>
                  <div v-if="editError" class="rounded-md bg-red-50 px-2 py-1.5 text-red-700 dark:bg-red-950/30 dark:text-red-300">
                    {{ editError }}
                  </div>
                </div>
              </section>

              <section class="border border-[var(--border-light)] bg-[var(--background-white-main)]" data-section="CapabilityAccess">
                <div class="border-b border-[var(--border-light)] px-3 py-2">
                  <h3 class="text-xs font-semibold uppercase text-[var(--text-tertiary)]">行为与权限</h3>
                </div>
                <div class="grid gap-3 p-3 text-xs xl:grid-cols-2">
                  <div class="min-w-0" data-section="SkillBindingSelector">
                    <div class="mb-1 flex items-center justify-between gap-2">
                      <span class="text-[var(--text-tertiary)]">技能权限</span>
                      <span class="font-mono text-[10px] text-[var(--text-tertiary)]">{{ editDraft.skill_refs.length }}</span>
                    </div>
                    <input
                      v-model="skillBindingQuery"
                      class="mb-2 h-8 w-full rounded-md border border-[var(--border-light)] bg-transparent px-2 text-[var(--text-primary)]"
                      placeholder="Filter skills"
                    />
                    <div class="max-h-48 overflow-auto border border-[var(--border-light)]">
                      <button
                        v-for="skill in filteredSkillCapabilities"
                        :key="skill.name"
                        class="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 border-b border-[var(--border-light)] px-2 py-1.5 text-left last:border-b-0 disabled:cursor-not-allowed disabled:opacity-55"
                        :disabled="!skill.available"
                        @click="toggleCapabilityBinding('skill_refs', skill.name)"
                      >
                        <input
                          type="checkbox"
                          class="h-3.5 w-3.5"
                          :checked="editDraft.skill_refs.includes(skill.name)"
                          :disabled="!skill.available"
                          tabindex="-1"
                          readonly
                        />
                        <span class="min-w-0">
                          <span class="block truncate font-mono text-[11px] text-[var(--text-primary)]">{{ skill.name }}</span>
                          <span class="block truncate text-[10px] text-[var(--text-tertiary)]">{{ capabilitySourceLabel(skill) }}</span>
                        </span>
                        <span class="rounded px-1.5 py-0.5 text-[10px]" :class="capabilityStatusClass(skill)">{{ capabilityStatusLabel(skill) }}</span>
                      </button>
                      <div v-if="!filteredSkillCapabilities.length" class="px-2 py-4 text-center text-[var(--text-tertiary)]">
                        No matching skills
                      </div>
                    </div>
                    <div v-if="missingSkillBindings.length" class="mt-2 rounded-md bg-red-50 px-2 py-1 text-[11px] text-red-700 dark:bg-red-950/30 dark:text-red-300">
                      missing: {{ missingSkillBindings.join(', ') }}
                    </div>
                  </div>

                  <div class="min-w-0" data-section="ToolBindingSelector">
                    <div class="mb-1 flex items-center justify-between gap-2">
                      <span class="text-[var(--text-tertiary)]">工具权限</span>
                      <span class="font-mono text-[10px] text-[var(--text-tertiary)]">{{ editDraft.allowed_tools.length }}</span>
                    </div>
                    <input
                      v-model="toolBindingQuery"
                      class="mb-2 h-8 w-full rounded-md border border-[var(--border-light)] bg-transparent px-2 text-[var(--text-primary)]"
                      placeholder="Filter tools"
                    />
                    <div class="max-h-48 overflow-auto border border-[var(--border-light)]">
                      <button
                        v-for="tool in filteredToolCapabilities"
                        :key="tool.name"
                        class="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 border-b border-[var(--border-light)] px-2 py-1.5 text-left last:border-b-0 disabled:cursor-not-allowed disabled:opacity-55"
                        :disabled="!tool.available"
                        @click="toggleCapabilityBinding('allowed_tools', tool.name)"
                      >
                        <input
                          type="checkbox"
                          class="h-3.5 w-3.5"
                          :checked="editDraft.allowed_tools.includes(tool.name)"
                          :disabled="!tool.available"
                          tabindex="-1"
                          readonly
                        />
                        <span class="min-w-0">
                          <span class="block truncate font-mono text-[11px] text-[var(--text-primary)]">{{ tool.name }}</span>
                          <span class="block truncate text-[10px] text-[var(--text-tertiary)]">{{ capabilitySourceLabel(tool) }}</span>
                        </span>
                        <span class="rounded px-1.5 py-0.5 text-[10px]" :class="capabilityStatusClass(tool)">{{ capabilityStatusLabel(tool) }}</span>
                      </button>
                      <div v-if="!filteredToolCapabilities.length" class="px-2 py-4 text-center text-[var(--text-tertiary)]">
                        No matching tools
                      </div>
                    </div>
                    <div v-if="missingToolBindings.length" class="mt-2 rounded-md bg-red-50 px-2 py-1 text-[11px] text-red-700 dark:bg-red-950/30 dark:text-red-300">
                      missing: {{ missingToolBindings.join(', ') }}
                    </div>
                  </div>
                  <div v-if="capabilityLoadError" class="rounded-md bg-red-50 px-2 py-1.5 text-red-700 dark:bg-red-950/30 dark:text-red-300 xl:col-span-2">
                    {{ capabilityLoadError }}
                  </div>
                </div>
              </section>
            </div>

            <div v-else class="mt-4 border border-[var(--border-light)] bg-[var(--background-white-main)] p-4 text-sm text-[var(--text-secondary)]">
              <div class="mb-2 flex items-center gap-2 font-medium text-[var(--text-primary)]">
                <Lock :size="15" />
                系统内置 Agent 只读
              </div>
              <p>general-purpose 由 DeepAgents runtime 管理。它在 Registry 中可见，但不允许编辑或由用户切换运行状态。</p>
            </div>
          </section>

          <aside v-if="sidePanelExpanded" class="min-w-0 space-y-4">
            <section class="border border-[var(--border-light)] bg-[var(--background-white-main)]">
              <div class="flex items-center justify-between border-b border-[var(--border-light)] px-3 py-2">
                <h3 class="text-xs font-semibold uppercase text-[var(--text-tertiary)]">验证结果</h3>
                <AlertCircle v-if="selectedValidation?.status === 'failed'" :size="14" class="text-red-500" />
                <CheckCircle2 v-else-if="selectedValidation?.status === 'passed'" :size="14" class="text-emerald-500" />
              </div>
              <div class="px-3 py-3 text-xs">
                <template v-if="selectedValidation">
                  <div class="mb-2 flex items-center justify-between">
                    <span class="text-[var(--text-tertiary)]">状态</span>
                    <span class="font-medium text-[var(--text-primary)]">{{ selectedValidation.status }}</span>
                  </div>
                  <div class="mb-2 flex flex-wrap gap-1.5">
                    <span v-for="check in selectedValidation.checks" :key="check" class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]">{{ check }}</span>
                  </div>
                  <pre v-if="selectedValidation.errors.length" class="max-h-32 overflow-auto whitespace-pre-wrap rounded bg-red-50 p-2 text-[11px] text-red-700 dark:bg-red-950/30 dark:text-red-300">{{ selectedValidation.errors.join('\n') }}</pre>
                  <pre v-else class="max-h-32 overflow-auto whitespace-pre-wrap rounded bg-[var(--fill-tsp-gray-main)] p-2 text-[11px] text-[var(--text-secondary)]">{{ formatValidationPreview(selectedValidation.example_result) }}</pre>
                </template>
                <div v-else class="text-[var(--text-tertiary)]">
                  {{ selectedAgent.editable ? '点击启动时会自动执行发布前验证。' : '系统内置 Agent 由 runtime 管理，无需自定义验证。' }}
                </div>
              </div>
            </section>

            <section class="border border-[var(--border-light)] bg-[var(--background-white-main)]" data-section="RecentRunsCollapsed">
              <button
                class="flex w-full items-center justify-between border-b border-[var(--border-light)] px-3 py-2 text-left"
                @click="recentRunsExpanded = !recentRunsExpanded"
              >
                <span class="text-xs font-semibold uppercase text-[var(--text-tertiary)]">最近运行</span>
                <span class="inline-flex items-center gap-2 text-[11px] text-[var(--text-tertiary)]">
                  {{ selectedAgentRuns.length }}
                  <ChevronDown :size="14" :class="{ 'rotate-180': recentRunsExpanded }" />
                </span>
              </button>
              <div v-if="recentRunsExpanded" class="divide-y divide-[var(--border-light)]">
                <div v-for="run in selectedAgentRuns" :key="run.task_id" class="px-3 py-2 text-xs">
                  <div class="flex items-center justify-between gap-2">
                    <span class="truncate font-mono text-[var(--text-primary)]">{{ run.task_id }}</span>
                    <span class="rounded bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5 text-[10px] text-[var(--text-secondary)]">{{ run.status }}</span>
                  </div>
                  <div class="mt-1 flex flex-wrap gap-2 text-[10px] text-[var(--text-tertiary)]">
                    <span>{{ formatRunTime(run.completed_at || run.started_at) }}</span>
                    <span>引用证据={{ run.citation_evidence ? '是' : '否' }}</span>
                  </div>
                </div>
                <div v-if="!selectedAgentRuns.length" class="px-3 py-5 text-xs text-[var(--text-tertiary)]">
                  暂无真实运行记录
                </div>
              </div>
            </section>
          </aside>
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
import {
  AlertCircle,
  BookOpenCheck,
  CheckCircle2,
  ChevronDown,
  Cpu,
  Lock,
  PanelRight,
  PauseCircle,
  Pencil,
  Power,
  RefreshCw,
  ShieldCheck,
} from 'lucide-vue-next';
import {
  listResearchAgentCapabilities,
  listResearchAgentRuns,
  listResearchAgents,
  updateResearchAgent,
  validateResearchAgent,
  type ResearchAgentCapabilities,
  type ResearchAgentCapabilityItem,
  type ResearchAgentDefinition,
  type ResearchAgentRun,
  type ResearchAgentUpdateRequest,
  type ResearchAgentValidationResult,
} from '../api/agent';

interface AgentEditDraft {
  display_name: string;
  description: string;
  system_prompt: string;
  skill_refs: string[];
  allowed_tools: string[];
}

const agents = ref<ResearchAgentDefinition[]>([]);
const selectedAgentName = ref('');
const loading = ref(false);
const loadingRunsAgentName = ref('');
const validatingAgentName = ref('');
const savingAgentName = ref('');
const editError = ref('');
const sidePanelExpanded = ref(false);
const recentRunsExpanded = ref(false);
const recentRuns = ref<Record<string, ResearchAgentRun[]>>({});
const validationResults = ref<Record<string, ResearchAgentValidationResult>>({});
const capabilities = ref<ResearchAgentCapabilities>({ skills: [], tools: [] });
const capabilityLoadError = ref('');
const skillBindingQuery = ref('');
const toolBindingQuery = ref('');
const editDraft = ref<AgentEditDraft>({
  display_name: '',
  description: '',
  system_prompt: '',
  skill_refs: [],
  allowed_tools: [],
});

const preferredAgentOrder = ['general-purpose', 'research_auditor', 'paper_reader_worker'];
const legacyDisplayNames: Record<string, string> = {
  'General Purpose': '通用执行 Agent',
  'Auditor Agent': '边界审计智能体',
  'Reader Worker': '阅读 Worker',
};
const legacyDescriptions: Record<string, string> = {
  'DeepAgents built-in general task worker.': 'DeepAgents 内置通用任务执行 Agent。它由 runtime 管理，只在 Registry 中只读展示。',
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
const skillCapabilityNames = computed(() => new Set(capabilities.value.skills.map(item => item.name)));
const toolCapabilityNames = computed(() => new Set(capabilities.value.tools.map(item => item.name)));
const filteredSkillCapabilities = computed(() => filterCapabilities(capabilities.value.skills, skillBindingQuery.value));
const filteredToolCapabilities = computed(() => filterCapabilities(capabilities.value.tools, toolBindingQuery.value));
const missingSkillBindings = computed(() => editDraft.value.skill_refs.filter(name => !skillCapabilityNames.value.has(name)));
const missingToolBindings = computed(() => editDraft.value.allowed_tools.filter(name => !toolCapabilityNames.value.has(name)));

const defaultSelectedAgentName = (items: ResearchAgentDefinition[]) => {
  const editableCustomAgent = items.find(agent => agent.editable && agent.agent_type === 'custom');
  return editableCustomAgent?.name || items[0]?.name || '';
};

const filterCapabilities = (items: ResearchAgentCapabilityItem[], query: string) => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return items;
  return items.filter(item => {
    const haystack = `${item.name} ${item.description || ''} ${item.source || ''}`.toLowerCase();
    return haystack.includes(normalizedQuery);
  });
};

const capabilitySourceLabel = (item: ResearchAgentCapabilityItem) => {
  const labels: Record<string, string> = {
    builtin_skill: 'built-in skill',
    external_skill: 'skill library',
    research_builtin: 'research tool',
    external_tool: 'tools library',
  };
  if (item.tool_pack?.id) {
    return `${labels[item.source] || item.source} / ${item.tool_pack.id}`;
  }
  return labels[item.source] || item.source;
};

const capabilityStatusLabel = (item: ResearchAgentCapabilityItem) => {
  if (item.blocked) return 'blocked';
  return item.available ? 'available' : 'missing';
};

const capabilityStatusClass = (item: ResearchAgentCapabilityItem) => {
  if (item.blocked || !item.available) {
    return 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300';
  }
  return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300';
};

const toggleCapabilityBinding = (field: 'skill_refs' | 'allowed_tools', name: string) => {
  const current = editDraft.value[field];
  editDraft.value = {
    ...editDraft.value,
    [field]: current.includes(name) ? current.filter(item => item !== name) : [...current, name],
  };
};

const displayAgentName = (agent: ResearchAgentDefinition) => legacyDisplayNames[agent.display_name] || agent.display_name;
const displayAgentDescription = (agent: ResearchAgentDefinition) => legacyDescriptions[agent.description] || agent.description;
const agentTypeLabel = (agent: ResearchAgentDefinition) => (
  agent.agent_type === 'system_builtin' ? '系统内置' : (agent.agent_type === 'custom' ? '用户自定义' : agent.agent_type)
);
const editabilityLabel = (agent: ResearchAgentDefinition) => (agent.editable ? '可编辑' : '只读');

const validationStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    passed: '已通过',
    failed: '未通过',
    valid: '已验证',
    invalid: '未通过',
    draft: '草稿',
    disabled: '已暂停',
    system_managed: '系统托管',
  };
  return labels[status] || status;
};

const availabilityActionLabel = (agent: ResearchAgentDefinition) => {
  if (savingAgentName.value === agent.name || validatingAgentName.value === agent.name) {
    return agent.enabled ? '暂停中' : '启动中';
  }
  return agent.enabled ? '暂停' : '启动';
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

const syncDraftFromAgent = (agent: ResearchAgentDefinition) => {
  editDraft.value = {
    display_name: displayAgentName(agent),
    description: agent.description,
    system_prompt: agent.system_prompt,
    skill_refs: [...agent.skill_refs],
    allowed_tools: [...agent.allowed_tools],
  };
};

const selectAgent = (agentName: string) => {
  selectedAgentName.value = agentName;
  sidePanelExpanded.value = false;
  recentRunsExpanded.value = false;
};

const startEditing = (agent: ResearchAgentDefinition) => {
  if (!agent.editable) return;
  editError.value = '';
  syncDraftFromAgent(agent);
};

const resetDraft = (agent: ResearchAgentDefinition) => {
  editError.value = '';
  syncDraftFromAgent(agent);
};

const replaceAgent = (updated: ResearchAgentDefinition) => {
  agents.value = agents.value.map(item => item.name === updated.name ? updated : item);
  if (selectedAgentName.value === updated.name) {
    syncDraftFromAgent(updated);
  }
};

const saveAgentEdits = async (agent: ResearchAgentDefinition) => {
  if (!agent.editable) return;
  editError.value = '';
  const payload: ResearchAgentUpdateRequest = {
    display_name: editDraft.value.display_name.trim(),
    description: editDraft.value.description.trim(),
    system_prompt: editDraft.value.system_prompt.trim(),
    skill_refs: [...editDraft.value.skill_refs],
    allowed_tools: [...editDraft.value.allowed_tools],
  };
  savingAgentName.value = agent.name;
  try {
    const updated = await updateResearchAgent(agent.name, payload);
    replaceAgent(updated);
    validationResults.value = Object.fromEntries(
      Object.entries(validationResults.value).filter(([name]) => name !== updated.name),
    );
  } catch (error) {
    editError.value = error instanceof Error ? error.message : String(error);
  } finally {
    if (savingAgentName.value === agent.name) {
      savingAgentName.value = '';
    }
  }
};

const toggleAgentEnabled = async (agent: ResearchAgentDefinition, enabled: boolean) => {
  if (!agent.editable) return;
  savingAgentName.value = agent.name;
  editError.value = '';
  try {
    const updated = await updateResearchAgent(agent.name, { enabled });
    replaceAgent(updated);
  } catch (error) {
    editError.value = error instanceof Error ? error.message : String(error);
  } finally {
    if (savingAgentName.value === agent.name) {
      savingAgentName.value = '';
    }
  }
};

const validateAndEnableAgent = async (agent: ResearchAgentDefinition) => {
  validatingAgentName.value = agent.name;
  editError.value = '';
  try {
    const validation = await validateResearchAgent(agent.name);
    validationResults.value = {
      ...validationResults.value,
      [agent.name]: validation,
    };
    if (validation.published) {
      replaceAgent(validation.published);
    }
  } catch (error) {
    editError.value = error instanceof Error ? error.message : String(error);
  } finally {
    if (validatingAgentName.value === agent.name) {
      validatingAgentName.value = '';
    }
  }
};

const toggleAgentAvailability = async (agent: ResearchAgentDefinition) => {
  if (!agent.editable) return;
  if (agent.enabled) {
    await toggleAgentEnabled(agent, false);
    return;
  }
  if (agent.validation_status === 'passed') {
    await toggleAgentEnabled(agent, true);
    return;
  }
  await validateAndEnableAgent(agent);
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

const refreshAgents = async () => {
  loading.value = true;
  capabilityLoadError.value = '';
  try {
    const [nextAgents, nextCapabilities] = await Promise.all([
      listResearchAgents(),
      listResearchAgentCapabilities(),
    ]);
    agents.value = nextAgents;
    capabilities.value = nextCapabilities;
    if (!agents.value.some(agent => agent.name === selectedAgentName.value)) {
      selectedAgentName.value = defaultSelectedAgentName(orderedAgents.value);
    }
    if (selectedAgent.value?.editable) {
      syncDraftFromAgent(selectedAgent.value);
    }
  } catch (error) {
    capabilityLoadError.value = error instanceof Error ? error.message : String(error);
  } finally {
    loading.value = false;
  }
};

watch(
  () => selectedAgent.value?.name,
  (agentName) => {
    if (agentName) {
      void loadAgentRuns(agentName);
      if (selectedAgent.value?.editable) {
        syncDraftFromAgent(selectedAgent.value);
      }
    }
  },
);

onMounted(refreshAgents);
</script>
