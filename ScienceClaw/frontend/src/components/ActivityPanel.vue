<template>
  <div
    ref="panelRef"
    v-if="isVisible"
    :class="{
      'h-full w-full top-0 ltr:right-0 rtl:left-0 z-50 fixed sm:sticky sm:top-0 sm:right-0 sm:h-[100vh] sm:ml-3 sm:py-3 sm:mr-4': isShow,
      'h-full overflow-hidden': !isShow
    }"
    :style="{ width: isShow ? `${panelWidth}px` : '0px', opacity: isShow ? '1' : '0', transition: '0.2s ease-in-out' }"
  >
    <div v-if="isShow" class="h-full flex flex-col bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl border border-gray-200/60 dark:border-gray-700/40 rounded-2xl shadow-lg overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
        <div class="flex items-center gap-2.5">
          <div v-if="isLoading" class="relative size-4 flex-shrink-0">
            <div class="absolute inset-0 rounded-full border-2 border-blue-200 dark:border-blue-800"></div>
            <div class="absolute inset-0 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
          </div>
          <div v-else-if="lastTurnHadError" class="size-4 rounded-full bg-amber-400 flex items-center justify-center flex-shrink-0 shadow-sm shadow-amber-400/20">
            <svg class="size-2.5 text-white" viewBox="0 0 16 16" fill="currentColor"><path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zM7.25 4.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zM8 11a1 1 0 100-2 1 1 0 000 2z"/></svg>
          </div>
          <div v-else class="size-4 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center flex-shrink-0 shadow-sm shadow-emerald-400/20">
            <svg class="size-2.5 text-white" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="2 6.5 5 9.5 10 3"/></svg>
          </div>
          <span class="text-[13px] font-bold" :class="isLoading ? 'text-blue-600 dark:text-blue-400' : lastTurnHadError ? 'text-amber-600 dark:text-amber-400' : 'text-gray-700 dark:text-gray-200'">{{ isLoading ? t('Reasoning') + '...' : (lastTurnHadError ? t('Reasoning failed') : t('Reasoning completed')) }}</span>
        </div>
        <button @click="handleClose" class="flex size-7 items-center justify-center cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
          <XIcon :size="14" class="text-gray-400 dark:text-gray-500" />
        </button>
      </div>

      <!-- Content: flex layout keeps all section headers visible -->
      <div class="flex-1 flex flex-col min-h-0 overflow-hidden">

        <template v-if="runtimeAuditItems.length > 0">
          <div
            @click="runtimeAuditExpanded = !runtimeAuditExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': runtimeAuditExpanded }" />
            <ShieldCheck :size="13" class="text-emerald-400 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="runtimeAuditExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              Recovered runtime audit
            </span>
            <span class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
              {{ visibleRuntimeAuditItems.length }}
            </span>
          </div>
          <div v-if="runtimeAuditExpanded" class="border-b border-gray-100 dark:border-gray-800 px-4 py-2 overflow-y-auto min-h-0 section-content-enter" style="flex: 0.7 1 0%; min-height: 44px;">
            <div class="text-[11px] leading-[1.5] text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-lg px-3 py-2 border border-[var(--border-light)]">
              <div class="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-[var(--text-tertiary)] mb-1.5">
                <span>context_boundary=process_trace</span>
                <span>citation_evidence=false</span>
                <button
                  type="button"
                  class="runtime-audit-export ml-auto inline-flex items-center gap-1 rounded-md border border-[var(--border-light)] bg-[var(--background-menu-white)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-secondary)] transition-colors hover:border-emerald-200 hover:text-emerald-700 dark:hover:border-emerald-800/50 dark:hover:text-emerald-300"
                  title="Export runtime audit"
                  @click.stop="handleRuntimeAuditExport"
                >
                  <DownloadIcon :size="11" />
                  <span>Export</span>
                </button>
              </div>
              <div v-if="runtimeAuditPackOptions.length > 1" class="runtime-audit-pack-filter flex flex-wrap gap-1 mb-2">
                <button v-for="option in runtimeAuditPackOptions" :key="option.id"
                  @click.stop="selectedRuntimeAuditPack = option.id"
                  class="px-1.5 py-0.5 rounded-md border text-[10px] font-mono transition-colors"
                  :class="selectedRuntimeAuditPack === option.id ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800/50' : 'bg-[var(--background-menu-white)] text-[var(--text-tertiary)] border-[var(--border-light)] hover:text-[var(--text-secondary)]'">
                  {{ option.label }} {{ option.count }}
                </button>
              </div>
              <div class="flex flex-col gap-2">
                <div v-for="item in visibleRuntimeAuditItems" :key="item.event_id || item.tool_call_id"
                  class="min-w-0 border-t border-[var(--border-light)] first:border-t-0 pt-2 first:pt-0">
                  <div class="flex items-center gap-2 min-w-0 font-mono text-[10px] text-[var(--text-tertiary)]">
                    <span class="text-[var(--text-secondary)] truncate">{{ item.function || item.name || item.tool_call_id }}</span>
                    <span>kind={{ item.summary.kind }}</span>
                    <span>result_sha256={{ item.summary.result_sha256.slice(0, 12) }}</span>
                  </div>
                  <div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                    <span>pack={{ item.summary.tool_pack?.label || 'Unpacked' }}</span>
                    <span v-if="item.summary.result_contract?.kind">contract={{ item.summary.result_contract.kind }}</span>
                    <span v-if="item.summary.truncated">truncated=true</span>
                  </div>
                  <div v-if="item.summary.preview != null" class="mt-1">
                    <div class="text-[10px] text-[var(--text-tertiary)] mb-1 uppercase font-semibold">Recovered runtime detail</div>
                    <pre class="whitespace-pre-wrap break-words font-mono text-[10px] text-[var(--text-secondary)] bg-[var(--background-menu-white)] rounded-md px-2 py-1.5 border border-[var(--border-light)] max-h-[96px] overflow-y-auto">{{ safeStringify(item.summary.preview) }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ═══ Thoughts Section ═══ -->
        <template v-if="thinkingItems.length > 0">
          <!-- Thoughts header -->
          <div
            @click="thinkingExpanded = !thinkingExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': thinkingExpanded }" />
            <Lightbulb :size="13" class="text-amber-400 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="isCurrentlyThinking || thinkingExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              {{ t('Thinking') }}
            </span>
            <div v-if="isCurrentlyThinking" class="flex gap-0.5 ml-0.5">
              <span v-for="d in 3" :key="d"
                class="w-[3px] h-[3px] rounded-full bg-blue-400 animate-bounce-dot"
                :style="{ 'animation-delay': `${(d-1) * 200}ms` }"></span>
            </div>
          </div>
          <!-- Thoughts content -->
          <div v-if="thinkingExpanded" ref="thoughtsContentRef"
            class="overflow-y-auto border-b border-gray-100 dark:border-gray-800 px-4 py-2 min-h-0 section-content-enter" style="flex: 1 1 0%; min-height: 60px;">
            <div class="px-3 py-2.5 text-[12px] leading-[1.7] text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50 rounded-xl whitespace-pre-wrap break-words font-mono border border-gray-100 dark:border-gray-700/50">
              {{ aggregatedThinkingContent }}
            </div>
            <div v-if="isCurrentlyThinking" class="flex items-center gap-2 text-[11px] text-blue-500 dark:text-blue-400 py-2 pl-1 mt-1">
              <span class="flex gap-0.5">
                <span class="size-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay: 0ms"></span>
                <span class="size-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay: 150ms"></span>
                <span class="size-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay: 300ms"></span>
              </span>
              {{ t('Thinking') }}...
            </div>
          </div>
        </template>

        <!-- ═══ To-dos Section ═══ -->
        <template v-if="plan && plan.steps.length > 0">
          <div
            @click="todosExpanded = !todosExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': todosExpanded }" />
            <ListChecks :size="13" class="text-violet-400 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="todosExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              {{ t('Task Progress') }}
            </span>
            <span class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">{{ planProgress }}</span>
          </div>
          <div v-if="todosExpanded" class="border-b border-gray-100 dark:border-gray-800 px-4 py-2 overflow-y-auto min-h-0 section-content-enter" style="flex: 0.8 1 0%; min-height: 40px;">
            <div class="w-full h-1 bg-[var(--border-light)] rounded-full overflow-hidden mb-2">
              <div class="h-full rounded-full transition-all duration-500 ease-out"
                :class="planCompleted ? 'bg-emerald-500' : 'bg-blue-500'"
                :style="{ width: planPercent + '%' }"></div>
            </div>
            <div class="flex flex-col gap-1">
              <div v-for="step in plan.steps" :key="step.id"
                @click="toggleStepFilter(step.id)"
                class="flex items-start gap-2 py-1 px-1.5 -mx-1.5 rounded-md cursor-pointer transition-colors select-none"
                :class="{
                  'bg-blue-50 dark:bg-blue-950/30 ring-1 ring-blue-200 dark:ring-blue-800/40': selectedStepId === step.id,
                  'hover:bg-[var(--fill-tsp-gray-main)]': selectedStepId !== step.id
                }"
              >
                <div class="flex-shrink-0 w-4 h-4 mt-0.5 flex items-center justify-center">
                  <svg v-if="step.status === 'completed'" class="w-3.5 h-3.5 text-emerald-500" viewBox="0 0 16 16" fill="currentColor">
                    <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zm3.78-9.72a.75.75 0 00-1.06-1.06L7 8.94 5.28 7.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.06 0l4.25-4.25z"/>
                  </svg>
                  <div v-else-if="step.status === 'running'" class="w-3 h-3 border-[1.5px] border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                  <div v-else class="w-3 h-3 rounded-full border-[1.5px] border-[var(--border-main)]"></div>
                </div>
                <span class="text-[12px] leading-4 flex-1 step-description"
                  :class="{
                    'text-[var(--text-primary)] font-medium': step.status === 'running' || selectedStepId === step.id,
                    'text-[var(--text-secondary)]': step.status === 'completed' && selectedStepId !== step.id,
                    'text-[var(--text-tertiary)]': step.status !== 'running' && step.status !== 'completed' && selectedStepId !== step.id
                  }">
                  {{ step.description }}
                </span>
                <span v-if="step.tools?.length" class="flex-shrink-0 text-[10px] font-mono text-[var(--text-tertiary)] mt-0.5">
                  {{ step.tools.length }}
                </span>
              </div>
            </div>
          </div>
        </template>

        <!-- ═══ Tools Section ═══ -->
        <template v-if="researchSidecar">
          <div
            @click="researchEvidenceExpanded = !researchEvidenceExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': researchEvidenceExpanded }" />
            <ShieldCheck :size="13" class="text-emerald-500 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="researchEvidenceExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              研究证据
            </span>
            <span class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
              {{ researchSidecar.citations?.length || 0 }}
            </span>
          </div>
          <div v-if="researchEvidenceExpanded" class="border-b border-gray-100 dark:border-gray-800 px-4 py-2 overflow-y-auto min-h-0 section-content-enter" style="flex: 1 1 0%; min-height: 80px;">
            <div class="flex flex-col gap-2 text-[11px] leading-[1.5] text-[var(--text-secondary)]">
              <div v-if="researchSidecar.audit" class="rounded-lg border border-[var(--border-light)] bg-[var(--fill-tsp-gray-main)] px-3 py-2">
                <div class="mb-1.5 flex items-center gap-2">
                  <span class="font-semibold text-[var(--text-secondary)]">证据审计</span>
                  <span class="rounded-md px-1.5 py-0.5 font-mono text-[10px]" :class="researchAuditStatusClass(researchSidecar.audit.status)">
                    {{ researchSidecar.audit.status }}
                  </span>
                  <span class="ml-auto font-mono text-[10px] text-[var(--text-tertiary)]">
                    {{ researchSidecar.audit.approved_claim_count }}/{{ researchSidecar.audit.claim_count }}
                  </span>
                </div>
                <div class="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                  <span>approved={{ researchSidecar.audit.approved_claim_count }}</span>
                  <span>partial={{ researchSidecar.audit.partial_claim_count || 0 }}</span>
                  <span>unsupported={{ researchSidecar.audit.unsupported_claim_count }}</span>
                  <span>invalid={{ researchSidecar.audit.invalid_source_count }}</span>
                </div>
                <div v-if="approvedResearchAuditClaims.length" class="mt-2 flex flex-col gap-1">
                  <div class="text-[10px] font-semibold text-[var(--text-tertiary)]">已支持 claims</div>
                  <div
                    v-for="(claim, claimIndex) in approvedResearchAuditClaims"
                    :key="`approved-${claimIndex}`"
                    class="rounded-md border border-[var(--border-light)] bg-[var(--background-menu-white)] px-2 py-1.5"
                  >
                    <div class="flex items-start gap-2">
                      <span class="min-w-0 flex-1 text-[var(--text-secondary)]">{{ claim.claim_text }}</span>
                      <span class="shrink-0 font-mono text-[10px] text-emerald-600 dark:text-emerald-300">
                        {{ claim.status }}
                      </span>
                    </div>
                    <div v-if="claim.notes.length" class="mt-1 text-[10px] text-[var(--text-tertiary)]">
                      {{ claim.notes.join(' ') }}
                    </div>
                  </div>
                </div>
                <div v-if="partialResearchAuditClaims.length" class="mt-2">
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 rounded-md border border-[var(--border-light)] bg-[var(--background-menu-white)] px-2 py-1.5 text-left transition-colors hover:border-sky-200 hover:text-sky-700 dark:hover:border-sky-800/50 dark:hover:text-sky-300"
                    @click.stop="partialAuditClaimsExpanded = !partialAuditClaimsExpanded"
                  >
                    <ChevronRightIcon :size="11"
                      class="shrink-0 text-[var(--text-tertiary)] transition-transform duration-150"
                      :class="{ 'rotate-90': partialAuditClaimsExpanded }" />
                    <span class="min-w-0 flex-1 text-[11px] font-semibold text-[var(--text-secondary)]">部分支持 claims</span>
                    <span class="shrink-0 font-mono text-[10px] text-[var(--text-tertiary)]">{{ partialResearchAuditClaims.length }}</span>
                  </button>
                  <div v-if="partialAuditClaimsExpanded && partialResearchAuditClaims.length" class="mt-1 flex flex-col gap-1">
                    <div
                      v-for="(claim, claimIndex) in partialResearchAuditClaims"
                      :key="`partial-${claimIndex}`"
                      class="rounded-md border border-[var(--border-light)] bg-[var(--background-menu-white)] px-2 py-1.5"
                    >
                      <div class="flex items-start gap-2">
                        <span class="min-w-0 flex-1 text-[var(--text-secondary)]">{{ claim.claim_text }}</span>
                        <span class="shrink-0 font-mono text-[10px] text-sky-600 dark:text-sky-300">
                          {{ claim.status }}
                        </span>
                      </div>
                      <div v-if="claim.notes.length" class="mt-1 text-[10px] text-[var(--text-tertiary)]">
                        {{ claim.notes.join(' ') }}
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="unsupportedResearchAuditClaims.length" class="mt-2">
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 rounded-md border border-[var(--border-light)] bg-[var(--background-menu-white)] px-2 py-1.5 text-left transition-colors hover:border-amber-200 hover:text-amber-700 dark:hover:border-amber-800/50 dark:hover:text-amber-300"
                    @click.stop="unsupportedAuditClaimsExpanded = !unsupportedAuditClaimsExpanded"
                  >
                    <ChevronRightIcon :size="11"
                      class="shrink-0 text-[var(--text-tertiary)] transition-transform duration-150"
                      :class="{ 'rotate-90': unsupportedAuditClaimsExpanded }" />
                    <span class="min-w-0 flex-1 text-[11px] font-semibold text-[var(--text-secondary)]">未支持 claims</span>
                    <span class="shrink-0 font-mono text-[10px] text-[var(--text-tertiary)]">{{ unsupportedResearchAuditClaims.length }}</span>
                  </button>
                  <div v-if="unsupportedAuditClaimsExpanded && unsupportedResearchAuditClaims.length" class="mt-1 flex flex-col gap-1">
                    <div
                      v-for="(claim, claimIndex) in unsupportedResearchAuditClaims"
                      :key="`unsupported-${claimIndex}`"
                      class="rounded-md border border-[var(--border-light)] bg-[var(--background-menu-white)] px-2 py-1.5"
                    >
                      <div class="flex items-start gap-2">
                        <span class="min-w-0 flex-1 text-[var(--text-secondary)]">{{ claim.claim_text }}</span>
                        <span class="shrink-0 font-mono text-[10px] text-amber-600 dark:text-amber-300">
                          {{ claim.status }}
                        </span>
                      </div>
                      <div v-if="claim.notes.length" class="mt-1 text-[10px] text-[var(--text-tertiary)]">
                        {{ claim.notes.join(' ') }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="researchSidecar.summary_synthesis" class="rounded-lg border border-[var(--border-light)] bg-[var(--fill-tsp-gray-main)] px-3 py-2">
                <div class="mb-1.5 flex items-center justify-between gap-2">
                  <span class="font-semibold text-[var(--text-secondary)]">综合阶段</span>
                  <span class="font-mono text-[10px] text-[var(--text-tertiary)]">{{ researchSidecar.summary_synthesis.mode }}</span>
                </div>
                <div class="grid gap-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                  <span v-if="researchSidecar.summary_synthesis.section_count != null">sections={{ researchSidecar.summary_synthesis.section_count }}</span>
                  <span v-if="researchSidecar.summary_synthesis.intermediate_boundary">intermediate={{ researchSidecar.summary_synthesis.intermediate_boundary }}</span>
                  <span v-if="researchSidecar.summary_synthesis.citation_source">citation_source={{ researchSidecar.summary_synthesis.citation_source }}</span>
                  <span v-if="researchSidecar.summary_synthesis.intermediate_sources?.length">sources={{ researchSidecar.summary_synthesis.intermediate_sources.join(',') }}</span>
                </div>
              </div>

              <div v-if="researchSidecar.citations?.length" class="rounded-lg border border-[var(--border-light)] bg-[var(--fill-tsp-gray-main)] px-3 py-2">
                <div class="mb-1.5 flex items-center justify-between gap-2">
                  <span class="font-semibold text-[var(--text-secondary)]">引用证据</span>
                  <span class="font-mono text-[10px] text-[var(--text-tertiary)]">{{ researchSidecar.citations.length }}</span>
                </div>
                <div class="flex flex-col gap-1.5">
                  <div
                    v-for="citation in researchSidecar.citations"
                    :key="citation.evidence_id"
                    class="rounded-md border border-[var(--border-light)] bg-[var(--background-menu-white)] px-2 py-1.5"
                  >
                    <div class="flex items-center gap-2">
                      <span class="min-w-0 flex-1 truncate font-semibold text-[var(--text-secondary)]">{{ citation.citation_label }}</span>
                      <span class="shrink-0 font-mono text-[10px] uppercase text-[var(--text-tertiary)]">{{ citation.source_type }}</span>
                      <span class="shrink-0 rounded bg-[var(--fill-tsp-white-main)] px-1.5 py-0.5 text-[10px] text-[var(--text-tertiary)]">{{ evidenceScopeLabel(citation.evidence_scope) }}</span>
                    </div>
                    <div class="mt-0.5 truncate text-[10px] text-[var(--text-tertiary)]">
                      {{ citation.title }} · {{ citation.section }}<span v-if="citation.page_start"> · p. {{ citation.page_start }}<template v-if="citation.page_end && citation.page_end !== citation.page_start">-{{ citation.page_end }}</template></span>
                    </div>
                    <div class="mt-1 line-clamp-3 whitespace-pre-wrap text-[11px] text-[var(--text-secondary)]">
                      {{ citation.quote }}
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="researchSidecar.context_boundaries" class="rounded-lg border border-[var(--border-light)] bg-[var(--fill-tsp-gray-main)] px-3 py-2">
                <div class="mb-1.5 font-semibold text-[var(--text-secondary)]">上下文边界</div>
                <div class="grid gap-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                  <span>citation={{ formatBoundaryValues(researchSidecar.context_boundaries.citation_evidence) }}</span>
                  <span>memory={{ formatBoundaryValues(researchSidecar.context_boundaries.context_only_memory) }}</span>
                  <span>trace={{ formatBoundaryValues(researchSidecar.context_boundaries.process_trace) }}</span>
                  <span>reasoning={{ formatBoundaryValues(researchSidecar.context_boundaries.model_reasoning) }}</span>
                </div>
              </div>

              <div v-if="researchSidecar.context_memory?.length" class="rounded-lg border border-[var(--border-light)] bg-[var(--fill-tsp-gray-main)] px-3 py-2">
                <div class="mb-1.5 flex items-center justify-between gap-2">
                  <span class="font-semibold text-[var(--text-secondary)]">上下文记忆</span>
                  <span class="font-mono text-[10px] text-[var(--text-tertiary)]">{{ researchSidecar.context_memory.length }}</span>
                </div>
                <div class="flex flex-col gap-1.5">
                  <div
                    v-for="memory in researchSidecar.context_memory"
                    :key="memory.memory_id"
                    class="rounded-md border border-[var(--border-light)] bg-[var(--background-menu-white)] px-2 py-1.5"
                  >
                    <div class="flex items-center gap-2">
                      <span class="min-w-0 flex-1 truncate font-semibold text-[var(--text-secondary)]">{{ memory.title || memory.memory_id }}</span>
                      <span
                        v-if="memory.memory_status === 'conflict'"
                        class="shrink-0 rounded-md bg-amber-50 px-1.5 py-0.5 font-mono text-[10px] text-amber-700 dark:bg-amber-950/30 dark:text-amber-300"
                      >
                        冲突
                      </span>
                      <span class="shrink-0 font-mono text-[10px] text-[var(--text-tertiary)]">{{ memory.layer }}</span>
                    </div>
                    <div class="mt-1 line-clamp-2 whitespace-pre-wrap text-[11px] text-[var(--text-secondary)]">
                      {{ memory.content }}
                    </div>
                    <div v-if="memory.conflicts_with?.length" class="mt-1 text-[10px] text-[var(--text-tertiary)]">
                      conflicts_with={{ memory.conflicts_with.join(',') }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-if="toolItems.length > 0 || isLoading">
          <!-- Tools header -->
          <div
            @click="toolsExpanded = !toolsExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': toolsExpanded }" />
            <WrenchIcon :size="13" class="text-blue-400 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="toolsExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              {{ t('tools') }}
            </span>
            <span v-if="selectedStepId"
              @click.stop="selectedStepId = null"
              class="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 border border-blue-200/60 dark:border-blue-800/40 cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors ml-1 font-bold">
              {{ visibleToolItems.length }}/{{ toolItems.length }}
              <span class="ml-0.5">&times;</span>
            </span>
            <span v-else-if="toolItems.length > 0" class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
              {{ toolItems.length }}
            </span>
          </div>
          <!-- Tools content (independently scrollable, auto-scroll to bottom) -->
          <div v-if="toolsExpanded" ref="toolsContentRef"
            class="min-h-0 overflow-y-auto px-4 py-2 section-content-enter" style="flex: 1.2 1 0%; min-height: 60px;">
            <div class="px-3 py-2 bg-[var(--fill-tsp-gray-main)] rounded-lg">
              <div class="flex flex-col gap-0.5">
                <!-- Empty state when filter yields no results -->
                <div v-if="selectedStepId && visibleToolItems.length === 0"
                  class="text-[11px] text-[var(--text-tertiary)] py-3 text-center">
                  No tools associated with this step
                </div>
                <template v-for="item in visibleToolItems" :key="item.id">
                  <div v-if="item.tool" class="py-0.5">
                    <!-- Tool header (always visible, click to toggle) -->
                    <div
                      @click="toggleToolExpand(item.id)"
                      class="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[var(--background-menu-white)] transition-colors cursor-pointer border border-transparent group/tool"
                      :class="{ 'bg-[var(--background-menu-white)] border-[var(--border-light)]': expandedToolIds.has(item.id) }"
                    >
                      <ChevronRightIcon :size="10"
                        class="text-[var(--text-tertiary)] transition-transform duration-150 flex-shrink-0"
                        :class="{ 'rotate-90': expandedToolIds.has(item.id) }" />
                      <span v-if="item.tool.tool_meta?.icon" class="flex-shrink-0 text-sm leading-none">{{ item.tool.tool_meta.icon }}</span>
                      <div v-else class="flex-shrink-0 flex items-center justify-center w-4 h-4 text-[var(--text-tertiary)]">
                        <LoadingSpinnerIcon v-if="item.tool.status === 'calling'" class="w-3.5 h-3.5 animate-spin" />
                        <ZapIcon v-else :size="14" />
                      </div>
                      <LoadingSpinnerIcon v-if="item.tool.status === 'calling' && item.tool.tool_meta?.icon" class="w-3 h-3 animate-spin text-blue-500 flex-shrink-0" />
                      <div class="flex items-center gap-1.5 min-w-0 flex-1 text-[11px] font-mono">
                        <span class="text-[var(--text-secondary)] font-semibold flex-shrink-0">{{ item.tool.function || item.tool.name }}</span>
                        <span v-if="item.tool.metadata?.subagent_lifecycle && !expandedToolIds.has(item.id)"
                          class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-900/40">
                          {{ item.tool.metadata.subagent_lifecycle.agent_name }}
                        </span>
                        <span v-if="getToolArg(item.tool) && !expandedToolIds.has(item.id)" class="text-[var(--text-tertiary)] truncate max-w-[180px]">{{ getToolArg(item.tool) }}</span>
                      </div>
                      <span v-if="item.tool.duration_ms != null && item.tool.status === 'called'"
                        class="flex-shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400">
                        {{ formatDuration(item.tool.duration_ms) }}
                      </span>
                    </div>

                    <!-- Expanded detail (input & output) -->
                    <div v-if="expandedToolIds.has(item.id)"
                      class="tool-detail-enter mt-1 ml-4 mr-1 flex flex-col gap-2 px-3 py-2.5 rounded-lg bg-[var(--background-menu-white)] border border-[var(--border-light)]">
                      <!-- Subagent lifecycle -->
                      <div v-if="item.tool.metadata?.subagent_lifecycle">
                        <div class="text-[10px] text-[var(--text-tertiary)] mb-1 uppercase tracking-wider font-semibold">Subagent</div>
                        <div class="text-[11px] leading-[1.5] text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-md px-2.5 py-2 border border-[var(--border-light)]">
                          <div class="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                            <span>agent={{ item.tool.metadata.subagent_lifecycle.agent_name }}</span>
                            <span>role={{ item.tool.metadata.subagent_lifecycle.agent_role }}</span>
                            <span>phase={{ item.tool.metadata.subagent_lifecycle.phase }}</span>
                            <span>boundary={{ item.tool.metadata.subagent_lifecycle.output_boundary }}</span>
                            <span>citation_evidence={{ item.tool.metadata.subagent_lifecycle.citation_evidence }}</span>
                          </div>
                          <div v-if="item.tool.metadata.subagent_lifecycle.description" class="mt-1 text-[11px] text-[var(--text-secondary)]">
                            {{ item.tool.metadata.subagent_lifecycle.description }}
                          </div>
                        </div>
                      </div>
                      <!-- Input -->
                      <div v-if="item.tool.args && Object.keys(item.tool.args).length > 0">
                        <div class="text-[10px] text-[var(--text-tertiary)] mb-1 uppercase tracking-wider font-semibold">Input</div>
                        <pre class="text-[11px] leading-[1.5] whitespace-pre-wrap break-words text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-md px-2.5 py-2 border border-[var(--border-light)] max-h-[200px] overflow-y-auto font-mono">{{ safeStringify(item.tool.args) }}</pre>
                      </div>
                      <!-- Output -->
                      <div v-if="item.tool.content != null">
                        <div class="text-[10px] text-[var(--text-tertiary)] mb-1 uppercase tracking-wider font-semibold">Output</div>
                        <pre class="text-[11px] leading-[1.5] whitespace-pre-wrap break-words text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-md px-2.5 py-2 border border-[var(--border-light)] max-h-[200px] overflow-y-auto font-mono">{{ safeStringify(item.tool.content) }}</pre>
                      </div>
                      <!-- Runtime summary -->
                      <div v-if="item.tool.runtime_result_summary">
                        <div class="text-[10px] text-[var(--text-tertiary)] mb-1 uppercase tracking-wider font-semibold">Runtime summary</div>
                        <div class="text-[11px] leading-[1.5] text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-md px-2.5 py-2 border border-[var(--border-light)]">
                          <div class="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                            <span>kind={{ item.tool.runtime_result_summary.kind }}</span>
                            <span>result_sha256={{ item.tool.runtime_result_summary.result_sha256.slice(0, 12) }}</span>
                            <span>context_boundary={{ item.tool.runtime_result_summary.context_boundary }}</span>
                            <span>citation_evidence={{ item.tool.runtime_result_summary.citation_evidence }}</span>
                            <span v-if="item.tool.runtime_result_summary.tool_pack?.label">pack={{ item.tool.runtime_result_summary.tool_pack.label }}</span>
                            <span v-if="item.tool.runtime_result_summary.truncated">truncated=true</span>
                          </div>
                          <pre class="mt-1 whitespace-pre-wrap break-words font-mono max-h-[120px] overflow-y-auto">{{ safeStringify(item.tool.runtime_result_summary.preview) }}</pre>
                        </div>
                      </div>
                      <!-- Loading state -->
                      <div v-if="item.tool.status === 'calling' && !item.tool.content"
                        class="flex items-center gap-2 text-[11px] text-[var(--text-tertiary)] py-2 justify-center">
                        <div class="w-3.5 h-3.5 border-[1.5px] border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        Running...
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
            <!-- Processing at bottom -->
            <div v-if="isLoading" class="flex items-center gap-2 text-[11px] text-blue-500 dark:text-blue-400 py-2 pl-1 mt-1">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
              </span>
              Processing...
            </div>
          </div>
        </template>

        <!-- ═══ Sandbox Preview Section ═══ -->
        <template v-if="researchTaskRouteSteps.length > 0">
          <div
            @click="researchTaskRouteExpanded = !researchTaskRouteExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': researchTaskRouteExpanded }" />
            <ListChecks :size="13" class="text-violet-500 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="researchTaskRouteExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              研究任务路由
            </span>
            <span class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
              {{ researchTaskRouteSteps.length }}
            </span>
          </div>
          <div v-if="researchTaskRouteExpanded" class="border-b border-gray-100 dark:border-gray-800 px-4 py-2 overflow-y-auto min-h-0 section-content-enter" style="flex: 0.55 1 0%; min-height: 44px;">
            <div class="flex flex-col gap-2">
              <div v-for="{ step, route } in researchTaskRouteSteps" :key="step.id"
                class="text-[11px] leading-[1.5] text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-lg px-3 py-2 border border-[var(--border-light)]">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="font-semibold text-[var(--text-secondary)] truncate">{{ step.description }}</span>
                  <span class="ml-auto flex-shrink-0 rounded-md bg-violet-50 px-1.5 py-0.5 font-mono text-[10px] text-violet-700 dark:bg-violet-950/30 dark:text-violet-300">
                    {{ route.route }}
                  </span>
                </div>
                <div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                  <span>decision_source={{ route.decision_source }}</span>
                  <span>scope={{ route.scope }}</span>
                  <span>needs_retrieval={{ route.needs_retrieval }}</span>
                  <span>confidence={{ route.confidence }}</span>
                  <span v-if="route.reason">reason={{ route.reason }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-if="evidenceAdmissionSteps.length > 0">
          <div
            @click="evidenceAdmissionExpanded = !evidenceAdmissionExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': evidenceAdmissionExpanded }" />
            <ShieldCheck :size="13" class="text-emerald-500 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="evidenceAdmissionExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              Evidence admission
            </span>
            <span class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
              {{ evidenceAdmissionSteps.length }}
            </span>
          </div>
          <div v-if="evidenceAdmissionExpanded" class="border-b border-gray-100 dark:border-gray-800 px-4 py-2 overflow-y-auto min-h-0 section-content-enter" style="flex: 0.65 1 0%; min-height: 44px;">
            <div class="flex flex-col gap-2">
              <div v-for="{ step, admission } in evidenceAdmissionSteps" :key="step.id"
                class="text-[11px] leading-[1.5] text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-lg px-3 py-2 border border-[var(--border-light)]">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="font-semibold text-[var(--text-secondary)] truncate">{{ step.description }}</span>
                  <span
                    class="ml-auto flex-shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[10px]"
                    :class="admission.decision === 'accepted'
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300'
                      : 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300'"
                  >
                    {{ admission.decision }}
                  </span>
                </div>
                <div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                  <span>top_k={{ admission.top_k }}</span>
                  <span>threshold={{ admission.threshold }}</span>
                  <span>accepted={{ admission.accepted_count }}</span>
                  <span>rejected={{ admission.rejected_count }}</span>
                  <span>highest={{ admission.highest_score ?? 'none' }}</span>
                  <span v-if="admission.reason">reason={{ admission.reason }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-if="sourceQualitySteps.length > 0">
          <div
            @click="sourceQualityExpanded = !sourceQualityExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': sourceQualityExpanded }" />
            <ShieldCheck :size="13" class="text-cyan-500 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="sourceQualityExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              Source quality
            </span>
            <span class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
              {{ sourceQualitySteps.length }}
            </span>
          </div>
          <div v-if="sourceQualityExpanded" class="border-b border-gray-100 dark:border-gray-800 px-4 py-2 overflow-y-auto min-h-0 section-content-enter" style="flex: 0.65 1 0%; min-height: 44px;">
            <div class="flex flex-col gap-2">
              <div v-for="{ step, quality } in sourceQualitySteps" :key="step.id"
                class="text-[11px] leading-[1.5] text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-lg px-3 py-2 border border-[var(--border-light)]">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="font-semibold text-[var(--text-secondary)] truncate">{{ step.description }}</span>
                  <span
                    class="ml-auto flex-shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[10px]"
                    :class="quality.status === 'citation_grade'
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300'
                      : 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300'"
                  >
                    {{ quality.status === 'citation_grade' ? 'citation_grade' : 'identity_incomplete' }}
                  </span>
                </div>
                <div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-[var(--text-tertiary)]">
                  <span>source_type={{ quality.source_type }}</span>
                  <span>citation_evidence=true</span>
                  <span>identity_fields={{ quality.identity_fields.join(',') || 'none' }}</span>
                  <span v-if="quality.missing_fields.length">missing={{ quality.missing_fields.join(',') }}</span>
                  <span v-else>missing=none</span>
                  <span v-if="quality.quality_warnings?.length">warnings={{ quality.quality_warnings.join(',') }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <SandboxPreview
          ref="sandboxPreviewRef"
          :mode="activeSandboxMode"
          :isLive="isSandboxLive"
          :history="sandboxHistory"
          @close="activeSandboxMode = 'none'"
        />

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { X as XIcon, ChevronRight as ChevronRightIcon, Zap as ZapIcon, Lightbulb, ListChecks, Wrench as WrenchIcon, ShieldCheck, Download as DownloadIcon } from 'lucide-vue-next';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
import LoadingSpinnerIcon from './icons/LoadingSpinnerIcon.vue';
import SandboxPreview from './SandboxPreview.vue';
import type { ResearchAnswerMetadata, ToolContent } from '../types/message';
import type { PlanEventData } from '../types/event';
import type { RuntimeResultAudit, RuntimeResultAuditFilters } from '../api/agent';
import type { SandboxPreviewMode } from '../utils/sandbox';
import { getPreviewMode } from '../utils/sandbox';
import { useResizeObserver } from '../composables/useResizeObserver';
import { eventBus } from '../utils/eventBus';
import { EVENT_SHOW_FILE_PANEL, EVENT_SHOW_TOOL_PANEL, EVENT_SHOW_ACTIVITY_PANEL } from '../constants/event';

export interface ActivityItem {
  id: string;
  type: 'thinking' | 'tool';
  timestamp: number;
  content?: string;
  tool?: ToolContent;
  collapsed?: boolean;
}

const props = withDefaults(defineProps<{
  items: ActivityItem[];
  plan?: PlanEventData;
  isLoading: boolean;
  lastTurnHadError?: boolean;
  runtimeAudit?: RuntimeResultAudit | null;
  researchSidecar?: ResearchAnswerMetadata | null;
}>(), { lastTurnHadError: false });

const emit = defineEmits<{
  (e: 'toolClick', tool: ToolContent): void;
  (e: 'close'): void;
  (e: 'exportRuntimeAudit', filters: RuntimeResultAuditFilters): void;
}>();

const panelRef = ref<HTMLElement>();
const thoughtsContentRef = ref<HTMLElement>();
const toolsContentRef = ref<HTMLElement>();
const sandboxPreviewRef = ref<InstanceType<typeof SandboxPreview>>();
const isShow = ref(false);
const visible = ref(true);

const activeSandboxMode = ref<SandboxPreviewMode>('none');
const isSandboxLive = computed(() => {
  if (!props.isLoading) return false;
  return activeSandboxMode.value !== 'none';
});

const { size: parentWidth } = useResizeObserver(panelRef, {
  target: 'parent',
  property: 'width'
});

const panelWidth = computed(() => Math.min(parentWidth.value / 2, 600));

// Section expand/collapse states
const thinkingExpanded = ref(true);
const todosExpanded = ref(true);
const toolsExpanded = ref(true);
const runtimeAuditExpanded = ref(false);
const researchTaskRouteExpanded = ref(false);
const sourceQualityExpanded = ref(false);
const evidenceAdmissionExpanded = ref(false);
const researchEvidenceExpanded = ref(true);
const partialAuditClaimsExpanded = ref(false);
const unsupportedAuditClaimsExpanded = ref(false);
const selectedRuntimeAuditPack = ref('all');

// Step filter: when a To-do step is selected, only show its associated tools
const selectedStepId = ref<string | null>(null);

const toggleStepFilter = (stepId: string) => {
  selectedStepId.value = selectedStepId.value === stepId ? null : stepId;
};

const stepToolCallIds = computed(() => {
  if (!selectedStepId.value || !props.plan) return null;
  const step = props.plan.steps.find(s => s.id === selectedStepId.value);
  if (!step?.tools?.length) return new Set<string>();
  return new Set(step.tools.map(t => t.tool_call_id));
});

const visibleToolItems = computed(() => {
  if (!stepToolCallIds.value) return toolItems.value;
  return toolItems.value.filter(
    item => item.tool && stepToolCallIds.value!.has(item.tool.tool_call_id)
  );
});

// Per-tool expand/collapse tracking
const expandedToolIds = reactive(new Set<string>());

const toggleToolExpand = (id: string) => {
  if (expandedToolIds.has(id)) {
    expandedToolIds.delete(id);
  } else {
    expandedToolIds.add(id);
  }
};

const safeStringify = (value: any): string => {
  const seen = new WeakSet<object>();
  try {
    const json = JSON.stringify(value ?? null, (key, v) => {
      if (key === '__proto__') return undefined;
      if (typeof v === 'object' && v !== null) {
        if (seen.has(v)) return '[Circular]';
        seen.add(v);
      }
      return v;
    }, 2);
    if (!json) return '';
    if (json.length > 10000) return json.slice(0, 10000) + '\n...';
    return json;
  } catch (e: any) {
    return String(e);
  }
};

const thinkingItems = computed(() =>
  props.items.filter(i => i.type === 'thinking' && i.content)
);

const toolItems = computed(() =>
  props.items.filter(i => i.type === 'tool')
);

const runtimeAuditItems = computed(() =>
  props.runtimeAudit?.runtime_results ?? []
);

type ActivityPlanStep = NonNullable<PlanEventData['steps']>[number];
type SourceQuality = NonNullable<NonNullable<ActivityPlanStep['metadata']>['source_quality']>;
type EvidenceAdmission = NonNullable<NonNullable<ActivityPlanStep['metadata']>['evidence_admission']>;
type ResearchTaskRoute = NonNullable<NonNullable<ActivityPlanStep['metadata']>['task_route']>;

const sourceQualitySteps = computed(() =>
  (props.plan?.steps ?? [])
    .map(step => ({ step, quality: step.metadata?.source_quality }))
    .filter((item): item is { step: ActivityPlanStep; quality: SourceQuality } => !!item.quality)
);

const evidenceAdmissionSteps = computed(() =>
  (props.plan?.steps ?? [])
    .map(step => ({ step, admission: step.metadata?.evidence_admission }))
    .filter((item): item is { step: ActivityPlanStep; admission: EvidenceAdmission } => !!item.admission)
);

const researchTaskRouteSteps = computed(() =>
  (props.plan?.steps ?? [])
    .map(step => ({ step, route: step.metadata?.task_route }))
    .filter((item): item is { step: ActivityPlanStep; route: ResearchTaskRoute } => !!item.route)
);

const approvedResearchAuditClaims = computed(() =>
  props.researchSidecar?.audit?.claims.filter(claim => claim.status === 'approved') ?? []
);

const partialResearchAuditClaims = computed(() =>
  props.researchSidecar?.audit?.claims.filter(claim => claim.status === 'partial') ?? []
);

const unsupportedResearchAuditClaims = computed(() =>
  props.researchSidecar?.audit?.claims.filter(claim => claim.status !== 'approved' && claim.status !== 'partial') ?? []
);

const formatBoundaryValues = (values?: string[]) => {
  return values?.length ? values.join(',') : 'none';
};

const evidenceScopeLabel = (scope?: string) => {
  return scope === 'project' ? '研究库' : '当前会话';
};

const researchAuditStatusClass = (status: string) => {
  switch (status) {
    case 'approved':
      return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300';
    case 'partial':
    case 'unsupported':
      return 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300';
    case 'invalid_source':
      return 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300';
    default:
      return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300';
  }
};

const runtimeAuditPackOptions = computed(() => {
  const packCounts = new Map<string, { id: string; label: string; count: number }>();
  for (const item of runtimeAuditItems.value) {
    const id = item.summary.tool_pack?.id || 'unpacked';
    const label = item.summary.tool_pack?.label || 'Unpacked';
    const existing = packCounts.get(id);
    if (existing) {
      existing.count += 1;
    } else {
      packCounts.set(id, { id, label, count: 1 });
    }
  }
  return [
    { id: 'all', label: 'All packs', count: runtimeAuditItems.value.length },
    ...Array.from(packCounts.values())
  ];
});

const visibleRuntimeAuditItems = computed(() => {
  if (selectedRuntimeAuditPack.value === 'all') return runtimeAuditItems.value;
  return runtimeAuditItems.value.filter(
    item => item.summary.tool_pack?.id === selectedRuntimeAuditPack.value ||
      (!item.summary.tool_pack?.id && selectedRuntimeAuditPack.value === 'unpacked')
  );
});

const handleRuntimeAuditExport = () => {
  const filters: RuntimeResultAuditFilters = selectedRuntimeAuditPack.value === 'all'
    ? {}
    : { tool_pack_id: selectedRuntimeAuditPack.value };
  emit('exportRuntimeAudit', filters);
};

watch(runtimeAuditPackOptions, (options) => {
  if (!options.some(option => option.id === selectedRuntimeAuditPack.value)) {
    selectedRuntimeAuditPack.value = 'all';
  }
});

const aggregatedThinkingContent = computed(() =>
  thinkingItems.value.map(i => (i.content || '').trim()).filter(Boolean).join('\n\n').replace(/\n{3,}/g, '\n\n')
);

const isCurrentlyThinking = computed(() => {
  if (!props.isLoading) return false;
  const lastItem = props.items[props.items.length - 1];
  return lastItem?.type === 'thinking';
});

const planProgress = computed(() => {
  const done = props.plan?.steps.filter(s => s.status === 'completed').length ?? 0;
  return `${done}/${props.plan?.steps.length ?? 0}`;
});

const planPercent = computed(() => {
  const total = props.plan?.steps.length ?? 1;
  const done = props.plan?.steps.filter(s => s.status === 'completed').length ?? 0;
  return Math.round((done / total) * 100);
});

const planCompleted = computed(() => props.plan?.steps.every(s => s.status === 'completed') ?? false);

const isVisible = computed(() => visible.value);

const getToolArg = (tool: ToolContent): string => {
  if (!tool.args) return '';
  const fn = tool.function || tool.name || '';
  if (fn.includes('search')) return tool.args.query || tool.args.search_query || '';
  if (fn.includes('exec') || fn === 'execute' || fn.startsWith('terminal_')) return tool.args.command || '';
  if (fn.includes('file') || fn === 'read_file' || fn === 'write_file' || fn === 'edit_file') return tool.args.file_path || tool.args.file || tool.args.path || '';
  if (fn.includes('crawl') || fn.startsWith('browser_')) return tool.args.url || '';
  if (fn.startsWith('markitdown_')) return tool.args.file || '';
  const vals = Object.values(tool.args);
  if (vals.length > 0 && typeof vals[0] === 'string') return (vals[0] as string).slice(0, 80);
  return '';
};

const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

const handleClose = () => {
  isShow.value = false;
  emit('close');
};

const scrollThoughtsToBottom = () => {
  nextTick(() => {
    if (thoughtsContentRef.value) {
      thoughtsContentRef.value.scrollTop = thoughtsContentRef.value.scrollHeight;
    }
  });
};

const scrollToolsToBottom = () => {
  nextTick(() => {
    if (toolsContentRef.value) {
      toolsContentRef.value.scrollTop = toolsContentRef.value.scrollHeight;
    }
  });
};

watch(aggregatedThinkingContent, scrollThoughtsToBottom);
watch(() => toolItems.value.length, scrollToolsToBottom);
watch(() => props.plan, () => {}, { deep: true });

/**
 * Extract a display-friendly command string from tool args.
 */
function extractCommand(tool: ToolContent): string {
  const args = tool.args;
  if (!args || typeof args !== 'object') return '';
  return args.command || args.code || args.script || args.path || args.file || args.url || args.action || '';
}

/**
 * Extract output text from tool result content.
 */
function extractOutput(tool: ToolContent): string {
  const c = tool.content;
  if (!c) return '';
  if (typeof c === 'string') {
    try {
      const parsed = JSON.parse(c);
      return parsed.stdout || parsed.output || parsed.text || c;
    } catch {
      return c;
    }
  }
  if (typeof c === 'object') {
    return (c as any).stdout || (c as any).output || (c as any).text || JSON.stringify(c);
  }
  return String(c);
}

// Track which tool calls we've already written to terminal
const writtenToolCalls = new Set<string>();

export interface SandboxExecEntry {
  toolName: string;
  command: string;
  output?: string;
  status: string;
}

const sandboxHistory = ref<SandboxExecEntry[]>([]);

function scanSandboxTools() {
  for (const item of props.items) {
    if (item.type !== 'tool' || !item.tool) continue;
    const fn = item.tool.function || item.tool.name || '';
    const isSandboxProxy = !!item.tool.tool_meta?.sandbox;
    const mode = getPreviewMode(fn, isSandboxProxy);
    if (mode === 'none') continue;

    const callId = item.tool.tool_call_id || item.id;

    if (item.tool.status === 'calling' && !writtenToolCalls.has(callId + ':calling')) {
      activeSandboxMode.value = mode;
      writtenToolCalls.add(callId + ':calling');
      sandboxHistory.value.push({ toolName: fn, command: extractCommand(item.tool!), status: 'calling' });
    }

    if (item.tool.status === 'called' && !writtenToolCalls.has(callId + ':called')) {
      activeSandboxMode.value = mode;
      if (!writtenToolCalls.has(callId + ':calling')) {
        writtenToolCalls.add(callId + ':calling');
        sandboxHistory.value.push({ toolName: fn, command: extractCommand(item.tool!), status: 'calling' });
      }
      writtenToolCalls.add(callId + ':called');
      sandboxHistory.value.push({ toolName: fn, command: extractCommand(item.tool!), output: extractOutput(item.tool!), status: 'called' });
    }
  }
}

// Watch both new items AND status changes on existing items
watch(() => props.items.map(i => `${i.id}:${i.tool?.status}`).join(','), scanSandboxTools);

const show = () => {
  eventBus.emit(EVENT_SHOW_ACTIVITY_PANEL);
  visible.value = true;
  isShow.value = true;
};

const hide = () => {
  isShow.value = false;
};

onMounted(() => {
  eventBus.on(EVENT_SHOW_FILE_PANEL, () => {
    visible.value = false;
  });
  eventBus.on(EVENT_SHOW_TOOL_PANEL, () => {
    visible.value = false;
  });
});

onUnmounted(() => {
  eventBus.off(EVENT_SHOW_FILE_PANEL);
  eventBus.off(EVENT_SHOW_TOOL_PANEL);
});

defineExpose({
  show,
  hide,
  isShow,
});
</script>

<style scoped>
.animate-bounce-dot {
  display: inline-block;
  animation: dot-animation 1.5s infinite;
}
@keyframes dot-animation {
  0% { transform: translateY(0); }
  20% { transform: translateY(-3px); }
  40% { transform: translateY(0); }
  100% { transform: translateY(0); }
}

.step-description {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.section-content-enter {
  animation: section-reveal 0.2s ease-out;
}
@keyframes section-reveal {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.tool-detail-enter {
  animation: tool-detail-slide 0.15s ease-out;
}
@keyframes tool-detail-slide {
  from {
    opacity: 0;
    max-height: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    max-height: 500px;
    transform: translateY(0);
  }
}
</style>
