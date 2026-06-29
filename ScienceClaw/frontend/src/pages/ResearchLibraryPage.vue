<template>
  <div class="flex h-full w-full min-w-0 flex-col overflow-hidden bg-[var(--background-gray-main)]">
    <div class="flex h-14 flex-shrink-0 items-center justify-between border-b border-[var(--border-light)] bg-[var(--background-white-main)] px-5">
      <div class="min-w-0">
        <h1 class="truncate text-base font-semibold text-[var(--text-primary)]">研究库</h1>
        <p class="mt-0.5 text-xs text-[var(--text-tertiary)]">按研究课题管理论文、解析结果与可引用证据资产</p>
      </div>
      <button
        class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] px-2.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)] disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="loadingProjects || loadingPapers"
        @click="refreshAll"
      >
        <RefreshCw :size="14" :class="{ 'animate-spin': loadingProjects || loadingPapers }" />
        刷新
      </button>
    </div>

    <div class="flex min-h-0 flex-1">
      <aside class="flex w-72 flex-shrink-0 flex-col border-r border-[var(--border-light)] bg-[var(--background-white-main)]">
        <form class="border-b border-[var(--border-light)] p-3" @submit.prevent="handleCreateProject">
          <label class="mb-1 block text-[11px] font-medium text-[var(--text-tertiary)]">新建课题</label>
          <input
            v-model="newProjectName"
            class="h-8 w-full rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] px-2 text-sm text-[var(--text-primary)] outline-none transition-colors placeholder:text-[var(--text-tertiary)] focus:border-blue-400"
            placeholder="课题名称"
          />
          <input
            v-model="newProjectDescription"
            class="mt-2 h-8 w-full rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] px-2 text-sm text-[var(--text-primary)] outline-none transition-colors placeholder:text-[var(--text-tertiary)] focus:border-blue-400"
            placeholder="课题说明"
          />
          <button
            class="mt-2 inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-lg bg-blue-500 px-2.5 text-xs font-medium text-white hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="creatingProject || !newProjectName.trim()"
          >
            <Plus :size="14" />
            {{ creatingProject ? '创建中' : '创建课题' }}
          </button>
        </form>

        <div class="min-h-0 flex-1 overflow-y-auto p-2">
          <button
            v-for="project in projects"
            :key="project.project_id"
            class="mb-1 w-full rounded-md border px-3 py-2 text-left transition-colors"
            :class="selectedProjectId === project.project_id
              ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-300'
              : 'border-transparent text-[var(--text-secondary)] hover:border-[var(--border-light)] hover:bg-gray-50 dark:hover:bg-white/5'"
            @click="selectProject(project.project_id)"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="truncate text-sm font-medium">{{ project.name }}</span>
              <span class="text-[10px] tabular-nums opacity-60">{{ project.paper_count }}</span>
            </div>
            <p class="mt-1 truncate text-xs opacity-70">{{ project.description || '暂无说明' }}</p>
            <div class="mt-1 flex gap-2 text-[10px] opacity-60">
              <span>{{ project.paper_count }} 篇论文</span>
              <span>{{ project.evidence_record_count }} 条证据</span>
            </div>
          </button>
          <div v-if="!projects.length && !loadingProjects" class="px-3 py-8 text-center text-xs text-[var(--text-tertiary)]">
            暂无研究课题
          </div>
        </div>
      </aside>

      <main class="min-w-0 flex-1 overflow-hidden">
        <div v-if="selectedProject" class="flex h-full flex-col">
          <div class="flex flex-shrink-0 items-center justify-between border-b border-[var(--border-light)] bg-white/70 px-5 py-3 dark:bg-[#161616]/70">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <BookOpen :size="16" class="text-blue-500" />
                <h2 class="truncate text-sm font-semibold text-[var(--text-primary)]">{{ selectedProject.name }}</h2>
              </div>
              <p class="mt-1 truncate text-xs text-[var(--text-tertiary)]">{{ selectedProject.description || '该课题下的论文会作为会话可检索的证据边界' }}</p>
            </div>
            <label
              class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border-light)] bg-[var(--background-white-main)] px-2.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-gray-main)]"
              :class="uploadingPaper ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'"
            >
              <Upload :size="14" :class="{ 'animate-pulse': uploadingPaper }" />
              {{ uploadingPaper ? '上传中' : '上传论文' }}
              <input class="hidden" type="file" accept=".pdf,.md,.txt" :disabled="uploadingPaper" @change="handlePaperUpload" />
            </label>
          </div>

          <div class="min-h-0 flex-1 overflow-auto p-4">
            <table class="w-full border-collapse text-left text-sm">
              <thead>
                <tr class="border-b border-[var(--border-light)] text-[11px] text-[var(--text-tertiary)]">
                  <th class="px-3 py-2 font-medium">论文</th>
                  <th class="px-3 py-2 font-medium">解析器</th>
                  <th class="px-3 py-2 font-medium">切片</th>
                  <th class="px-3 py-2 font-medium">可引用证据</th>
                  <th class="px-3 py-2 font-medium">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="paper in papers" :key="paper.paper_id" class="border-b border-[var(--border-light)] bg-[var(--background-white-main)]/70 hover:bg-[var(--fill-tsp-gray-main)]">
                  <td class="max-w-[520px] px-3 py-2">
                    <div class="truncate font-medium text-[var(--text-primary)]">{{ paper.title }}</div>
                    <div class="truncate text-xs text-[var(--text-tertiary)]">{{ paper.authors.join(', ') || paper.paper_id }}</div>
                  </td>
                  <td class="px-3 py-2 text-xs text-[var(--text-secondary)]">{{ paper.parser }}</td>
                  <td class="px-3 py-2 text-xs tabular-nums text-[var(--text-secondary)]">{{ paper.chunk_count }}</td>
                  <td class="px-3 py-2 text-xs tabular-nums text-[var(--text-secondary)]">{{ paper.evidence_record_count }}</td>
                  <td class="px-3 py-2">
                    <span
                      class="inline-flex rounded px-1.5 py-0.5 text-[11px] font-medium"
                      :class="paper.citation_ready ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'"
                    >
                      {{ statusLabel(paper.status) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="!papers.length && !loadingPapers" class="flex h-48 items-center justify-center text-sm text-[var(--text-tertiary)]">
              暂无论文
            </div>
          </div>
        </div>
        <div v-else class="flex h-full items-center justify-center text-sm text-[var(--text-tertiary)]">
          请选择或新建一个研究课题
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { BookOpen, Plus, RefreshCw, Upload } from 'lucide-vue-next';
import {
  createResearchProject,
  listResearchProjectPapers,
  listResearchProjects,
  uploadResearchProjectPaper,
  type ResearchProject,
  type ResearchProjectPaperAsset,
} from '../api/agent';

const projects = ref<ResearchProject[]>([]);
const papers = ref<ResearchProjectPaperAsset[]>([]);
const selectedProjectId = ref('');
const newProjectName = ref('');
const newProjectDescription = ref('');
const loadingProjects = ref(false);
const loadingPapers = ref(false);
const creatingProject = ref(false);
const uploadingPaper = ref(false);

const selectedProject = computed(() => projects.value.find(project => project.project_id === selectedProjectId.value) || null);

const statusLabel = (status: string) => {
  const labels: Record<string, string> = {
    uploaded: '已上传',
    parsed: '已解析',
    indexed: '已索引',
  };
  return labels[status] || status;
};

const refreshProjects = async () => {
  loadingProjects.value = true;
  try {
    projects.value = await listResearchProjects();
    if (!selectedProjectId.value && projects.value.length > 0) {
      selectedProjectId.value = projects.value[0].project_id;
    }
  } finally {
    loadingProjects.value = false;
  }
};

const refreshPapers = async () => {
  if (!selectedProjectId.value) {
    papers.value = [];
    return;
  }
  loadingPapers.value = true;
  try {
    papers.value = await listResearchProjectPapers(selectedProjectId.value);
  } finally {
    loadingPapers.value = false;
  }
};

const refreshAll = async () => {
  await refreshProjects();
  await refreshPapers();
};

const selectProject = async (projectId: string) => {
  selectedProjectId.value = projectId;
  await refreshPapers();
};

const handleCreateProject = async () => {
  const name = newProjectName.value.trim();
  if (!name) return;
  creatingProject.value = true;
  try {
    const project = await createResearchProject({
      name,
      description: newProjectDescription.value.trim(),
    });
    newProjectName.value = '';
    newProjectDescription.value = '';
    await refreshProjects();
    selectedProjectId.value = project.project_id;
    await refreshPapers();
  } finally {
    creatingProject.value = false;
  }
};

const handlePaperUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file || !selectedProjectId.value || uploadingPaper.value) return;
  uploadingPaper.value = true;
  try {
    await uploadResearchProjectPaper(selectedProjectId.value, file);
    await refreshAll();
  } finally {
    uploadingPaper.value = false;
  }
};

onMounted(refreshAll);
</script>
