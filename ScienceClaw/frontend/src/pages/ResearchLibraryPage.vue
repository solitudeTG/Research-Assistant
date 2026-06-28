<template>
  <div class="flex h-full w-full min-w-0 flex-col overflow-hidden bg-[#f8f9fb] dark:bg-[#111]">
    <div class="flex h-14 flex-shrink-0 items-center justify-between border-b border-[var(--border-light)] bg-white/85 px-5 dark:bg-[#1a1a1a]/85">
      <div class="min-w-0">
        <h1 class="truncate text-base font-semibold text-[var(--text-primary)]">Research Library</h1>
        <p class="mt-0.5 text-xs text-[var(--text-tertiary)]">Project-scoped papers and citation-ready assets</p>
      </div>
      <button
        class="inline-flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-light)] bg-white px-2.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-gray-50 dark:bg-[#202020] dark:hover:bg-white/5"
        @click="refreshAll"
      >
        <RefreshCw :size="14" />
        Refresh
      </button>
    </div>

    <div class="flex min-h-0 flex-1">
      <aside class="flex w-72 flex-shrink-0 flex-col border-r border-[var(--border-light)] bg-white/80 dark:bg-[#1a1a1a]/80">
        <form class="border-b border-[var(--border-light)] p-3" @submit.prevent="handleCreateProject">
          <label class="mb-1 block text-[11px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">New Project</label>
          <input
            v-model="newProjectName"
            class="h-8 w-full rounded-md border border-[var(--border-light)] bg-white px-2 text-sm text-[var(--text-primary)] outline-none focus:border-emerald-400 dark:bg-[#202020]"
            placeholder="Project name"
          />
          <input
            v-model="newProjectDescription"
            class="mt-2 h-8 w-full rounded-md border border-[var(--border-light)] bg-white px-2 text-sm text-[var(--text-primary)] outline-none focus:border-emerald-400 dark:bg-[#202020]"
            placeholder="Description"
          />
          <button
            class="mt-2 inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-md bg-emerald-600 px-2.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="creatingProject || !newProjectName.trim()"
          >
            <Plus :size="14" />
            Create Project
          </button>
        </form>

        <div class="min-h-0 flex-1 overflow-y-auto p-2">
          <button
            v-for="project in projects"
            :key="project.project_id"
            class="mb-1 w-full rounded-md border px-3 py-2 text-left transition-colors"
            :class="selectedProjectId === project.project_id
              ? 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200'
              : 'border-transparent text-[var(--text-secondary)] hover:border-[var(--border-light)] hover:bg-gray-50 dark:hover:bg-white/5'"
            @click="selectProject(project.project_id)"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="truncate text-sm font-medium">{{ project.name }}</span>
              <span class="text-[10px] tabular-nums opacity-60">{{ project.paper_count }}</span>
            </div>
            <p class="mt-1 truncate text-xs opacity-70">{{ project.description || 'No description' }}</p>
            <div class="mt-1 flex gap-2 text-[10px] opacity-60">
              <span>{{ project.chunk_count }} chunks</span>
              <span>{{ project.evidence_record_count }} evidence</span>
            </div>
          </button>
          <div v-if="!projects.length && !loadingProjects" class="px-3 py-8 text-center text-xs text-[var(--text-tertiary)]">
            No research projects yet
          </div>
        </div>
      </aside>

      <main class="min-w-0 flex-1 overflow-hidden">
        <div v-if="selectedProject" class="flex h-full flex-col">
          <div class="flex flex-shrink-0 items-center justify-between border-b border-[var(--border-light)] bg-white/70 px-5 py-3 dark:bg-[#161616]/70">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <BookOpen :size="16" class="text-emerald-600" />
                <h2 class="truncate text-sm font-semibold text-[var(--text-primary)]">{{ selectedProject.name }}</h2>
              </div>
              <p class="mt-1 truncate text-xs text-[var(--text-tertiary)]">{{ selectedProject.description || 'Project asset boundary' }}</p>
            </div>
            <label class="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-[var(--border-light)] bg-white px-2.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-gray-50 dark:bg-[#202020] dark:hover:bg-white/5">
              <Upload :size="14" />
              Upload Paper
              <input class="hidden" type="file" accept=".pdf,.md,.txt" @change="handlePaperUpload" />
            </label>
          </div>

          <div class="min-h-0 flex-1 overflow-auto p-4">
            <table class="w-full border-collapse text-left text-sm">
              <thead>
                <tr class="border-b border-[var(--border-light)] text-[11px] uppercase tracking-wide text-[var(--text-tertiary)]">
                  <th class="px-3 py-2 font-medium">Paper</th>
                  <th class="px-3 py-2 font-medium">Parser</th>
                  <th class="px-3 py-2 font-medium">Chunks</th>
                  <th class="px-3 py-2 font-medium">Evidence</th>
                  <th class="px-3 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="paper in papers" :key="paper.paper_id" class="border-b border-[var(--border-light)] bg-white/70 dark:bg-[#1a1a1a]/60">
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
                      :class="paper.citation_ready ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'"
                    >
                      {{ paper.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="!papers.length && !loadingPapers" class="flex h-48 items-center justify-center text-sm text-[var(--text-tertiary)]">
              No papers in this project
            </div>
          </div>
        </div>
        <div v-else class="flex h-full items-center justify-center text-sm text-[var(--text-tertiary)]">
          Select or create a Research Project
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
