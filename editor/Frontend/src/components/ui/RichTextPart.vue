<template>
  <div class="rich-text-part text-gray-700 break-words">
    <div v-if="isPlainText" class="whitespace-pre-wrap">{{ normalizedText }}</div>

    <div v-else class="space-y-2">
      <template v-for="(block, index) in blocks" :key="`${block.type}-${index}`">
        <h1
          v-if="block.type === 'heading' && block.level === 1"
          class="text-lg mt-1 font-semibold text-gray-800 leading-snug"
          v-html="block.html"
        />

        <h2
          v-else-if="block.type === 'heading' && block.level === 2"
          class="text-base mt-1 font-semibold text-gray-800 leading-snug"
          v-html="block.html"
        />

        <h3
          v-else-if="block.type === 'heading'"
          class="text-sm mt-1 font-semibold text-gray-800 leading-snug"
          v-html="block.html"
        />

        <p
          v-else-if="block.type === 'paragraph'"
          class="leading-relaxed whitespace-normal"
          v-html="block.html"
        />

        <blockquote
          v-else-if="block.type === 'blockquote'"
          class="border-l-4 border-[#84A65B] pl-3 py-1 bg-white/50 text-gray-600 rounded-r"
          v-html="block.html"
        />

        <ul v-else-if="block.type === 'ul'" class="list-disc pl-5 space-y-1">
          <li v-for="(item, itemIndex) in block.items" :key="itemIndex" v-html="item" />
        </ul>

        <ol v-else-if="block.type === 'ol'" class="list-decimal pl-5 space-y-1">
          <li v-for="(item, itemIndex) in block.items" :key="itemIndex" v-html="item" />
        </ol>

        <div v-else-if="block.type === 'code'" class="rounded border border-gray-300 bg-[#1f2933] overflow-hidden">
          <div class="flex items-center justify-between gap-2 px-3 py-1.5 bg-black/25 text-xs text-gray-200">
            <span class="truncate">{{ block.language || 'text' }}</span>
            <button
              class="px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 text-gray-100 transition-colors"
              type="button"
              @click="copyCode(block.text)"
            >
              {{ copiedText === block.text ? '已复制' : '复制' }}
            </button>
          </div>
          <pre class="m-0 p-3 overflow-x-auto text-sm leading-relaxed text-gray-100"><code>{{ block.text }}</code></pre>
        </div>

        <div v-else-if="block.type === 'table'" class="overflow-x-auto rounded border border-gray-300 bg-white/60">
          <table class="min-w-full text-sm border-collapse">
            <thead class="bg-gray-100 text-gray-700">
              <tr>
                <th
                  v-for="(cell, cellIndex) in block.header"
                  :key="cellIndex"
                  class="border border-gray-300 px-2 py-1.5 text-left font-semibold"
                  v-html="cell"
                />
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
                <td
                  v-for="(cell, cellIndex) in row"
                  :key="cellIndex"
                  class="border border-gray-300 px-2 py-1.5 align-top"
                  v-html="cell"
                />
              </tr>
            </tbody>
          </table>
        </div>

        <hr v-else-if="block.type === 'hr'" class="border-gray-300" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue';
import { looksLikeMarkdown, parseMarkdown, renderPlainTextBlock } from '@/utils/richTextMarkdown.js';

const props = defineProps({
  text: {
    type: String,
    default: '',
  },
  format: {
    type: String,
    default: 'auto',
  },
  streaming: {
    type: Boolean,
    default: false,
  },
});

const copiedText = ref('');
const renderedText = ref('');
let renderTimer = null;

const normalizedText = computed(() => (props.text == null ? '' : String(props.text)));
const isPlainText = computed(() => {
  const format = String(props.format || 'auto').toLowerCase();
  if (format === 'plain' || format === 'text/plain') {
    return true;
  }
  if (format === 'markdown' || format === 'text/markdown' || format === 'md') {
    return false;
  }
  return !looksLikeMarkdown(renderedText.value);
});

const blocks = computed(() => {
  try {
    return parseMarkdown(renderedText.value);
  } catch {
    return [renderPlainTextBlock(renderedText.value)];
  }
});

watch(
  () => [normalizedText.value, props.streaming],
  ([text, streaming]) => {
    if (renderTimer) {
      clearTimeout(renderTimer);
      renderTimer = null;
    }

    if (!streaming) {
      renderedText.value = text;
      return;
    }

    renderTimer = setTimeout(() => {
      renderedText.value = text;
      renderTimer = null;
    }, 120);
  },
  { immediate: true },
);

onUnmounted(() => {
  if (renderTimer) {
    clearTimeout(renderTimer);
    renderTimer = null;
  }
});

async function copyCode(text) {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    copiedText.value = text;
    setTimeout(() => {
      if (copiedText.value === text) {
        copiedText.value = '';
      }
    }, 1200);
  } catch {
    copiedText.value = '';
  }
}

</script>

<style scoped>
.rich-text-part :deep(a) {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.rich-text-part :deep(code) {
  border-radius: 4px;
  background: rgba(31, 41, 55, 0.08);
  padding: 0.1rem 0.25rem;
  font-size: 0.92em;
}

.rich-text-part pre code {
  background: transparent;
  padding: 0;
}
</style>