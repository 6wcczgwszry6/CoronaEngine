<template>
  <div ref="selectRef" class="custom-select" :class="{ open: isOpen }">
    <div class="select-trigger" @click="toggle">
      <span class="selected-value">{{ selectedLabel || placeholder }}</span>
      <span class="arrow">▼</span>
    </div>
    <div v-if="isOpen" class="select-dropdown">
      <div
        v-for="option in options"
        :key="option.value"
        class="select-option"
        :class="{ selected: option.value === modelValue }"
        @click="selectOption(option)"
      >
        {{ option.label }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({
  modelValue: [String, Number],
  options: Array,
  placeholder: { type: String, default: '请选择' },
});
const emit = defineEmits(['update:modelValue']);

const isOpen = ref(false);
const selectRef = ref(null);

const selectedLabel = computed(() => {
  const opt = props.options.find((o) => o.value === props.modelValue);
  return opt ? opt.label : '';
});

const toggle = () => {
  isOpen.value = !isOpen.value;
};

const selectOption = (option) => {
  emit('update:modelValue', option.value);
  isOpen.value = false;
};

const handleClickOutside = (e) => {
  if (selectRef.value && !selectRef.value.contains(e.target)) {
    isOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.custom-select {
  position: relative;
  display: inline-block;
  min-width: 120px;
  background: #3c3c3c;
  border: none;
  color: white;
  cursor: pointer;
}
.select-trigger {
  padding: 2px 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.arrow {
  font-size: 12px;
  margin-left: 8px;
}
.select-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #3c3c3c;
  border: 1px solid #555;
  max-height: 200px;
  overflow-y: auto;
  z-index: 1000;
}
.select-option {
  padding: 4px 8px;
  cursor: pointer;
}
.select-option:hover {
  background: #555;
}
.select-option.selected {
  background: #84a65b;
  color: white;
}
</style>
