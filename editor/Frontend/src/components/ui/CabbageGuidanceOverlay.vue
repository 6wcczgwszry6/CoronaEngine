<template>
  <Teleport to="body">
    <div
      v-if="guidance.state.active"
      class="guidance-overlay"
      role="dialog"
      aria-modal="true"
      :aria-label="guidance.state.guidance?.title || t('cabbageGuidance.title')"
      @mousedown.stop
      @pointerdown.stop
      @click.stop
      @wheel.prevent.stop
    >
      <div v-if="highlightStyle" class="guidance-highlight" :style="highlightStyle"></div>
      <section class="guidance-card">
        <div class="guidance-card-head">
          <strong>{{ guidance.state.guidance?.title || t('cabbageGuidance.title') }}</strong>
          <span>{{ guidance.state.stepIndex + 1 }} / {{ guidance.state.guidance?.steps?.length || 1 }}</span>
        </div>
        <p>{{ localizedStepText }}</p>
        <div class="guidance-actions">
          <button type="button" :disabled="guidance.state.stepIndex <= 0" @click="guidance.previous()">{{ t('cabbageGuidance.previous') }}</button>
          <button type="button" class="primary" @click="guidance.next()">
            {{ isLast ? t('cabbageGuidance.complete') : t('cabbageGuidance.next') }}
          </button>
          <button type="button" @click="guidance.stop()">{{ t('cabbageGuidance.stop') }}</button>
        </div>
        <small>{{ t('cabbageGuidance.safeNotice') }}</small>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { guidanceService as guidance } from '@/services/cabbageGuidanceService.js';

const { t, locale } = useI18n();
const step = computed(() => guidance.state.guidance?.steps?.[guidance.state.stepIndex] || null);
const localizedStepText = computed(() => {
  const current = step.value || {};
  if (locale.value === 'en-US') return current.textEn || current.text || t('cabbageGuidance.fallbackText');
  return current.text || current.textEn || t('cabbageGuidance.fallbackText');
});const isLast = computed(() => guidance.state.stepIndex >= (guidance.state.guidance?.steps?.length || 1) - 1);
const rect = computed(() => guidance.state.targetRect);

const highlightStyle = computed(() => {
  const value = rect.value;
  if (!value) return null;
  return {
    left: `${value.left - 5}px`, top: `${value.top - 5}px`,
    width: `${value.width + 10}px`, height: `${value.height + 10}px`,
  };
});

function onKeydown(event) {
  if (event.key === 'Escape' && guidance.state.active) {
    event.preventDefault();
    void guidance.stop();
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown, true));
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown, true));
</script>

<style scoped>
.guidance-overlay { position:fixed; inset:0; z-index:2147483600; pointer-events:auto; overflow:hidden; }
.guidance-highlight { position:fixed; border:2px solid #f2cf73; border-radius:9px; box-shadow:0 0 0 9999px rgba(0,0,0,.58),0 0 0 4px rgba(216,184,108,.2),0 0 26px rgba(242,207,115,.72); animation:guide-pulse 1.25s ease-in-out infinite; }
.guidance-card { position:fixed; left:50%; bottom:26px; width:min(480px,calc(100% - 32px)); transform:translateX(-50%); border:1px solid #8c6f36; border-radius:10px; background:#15130d; box-shadow:0 18px 50px rgba(0,0,0,.7); padding:13px 14px; color:#f2ead5; }
.guidance-card-head { display:flex; align-items:center; justify-content:space-between; gap:12px; color:#e5c77f; font-size:13px; }
.guidance-card-head span { color:#9d9278; font-size:11px; }
.guidance-card p { margin:8px 0 11px; color:#d8cfb7; font-size:12px; line-height:1.65; white-space:pre-wrap; }
.guidance-actions { display:flex; justify-content:flex-end; gap:7px; }
.guidance-actions button { border:1px solid #55431f; border-radius:5px; background:#211d12; color:#e9dfc5; padding:6px 11px; font-size:11px; }
.guidance-actions button:disabled { opacity:.38; }
.guidance-actions .primary { border-color:#b8924a; background:#6d5226; color:#fff7dc; }
.guidance-card small { display:block; margin-top:8px; color:#8f856e; font-size:10px; }
@keyframes guide-pulse { 50% { box-shadow:0 0 0 9999px rgba(0,0,0,.58),0 0 0 7px rgba(216,184,108,.12),0 0 34px rgba(242,207,115,.86); } }
</style>
