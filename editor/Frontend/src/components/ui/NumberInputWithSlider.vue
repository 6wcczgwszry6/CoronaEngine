<!-- components/ui/NumberInputWithSlider.vue -->
<template>
  <div class="number-input-slider flex flex-col gap-1 w-full min-w-0">
    <div class="number-input-row flex items-center w-full min-w-0" :class="compact ? 'gap-1' : 'gap-2'">
      <input
        ref="inputRef"
        type="text"
        :value="displayValue"
        :step="step"
        class="flex-1 min-w-0 bg-[#1a1a1a] text-[#e0e0e0] text-[10px] rounded px-2 py-0.5 outline-none border border-[#3c3c3c] focus:border-[#84a65b]"
        :style="{ textAlign: 'right' }"
        @input="handleNumberInput"
        @blur="handleBlur"
        @keydown="handleKeydown"
      />
      <span v-if="!compact" class="number-input-value text-[#84a65b] text-[9px] min-w-[35px] text-right font-mono">
        {{ formatValue }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  modelValue: {
    type: Number,
    default: 0,
  },
  step: {
    type: Number,
    default: 0.1,
  },
  min: {
    type: Number,
    default: undefined,
  },
  max: {
    type: Number,
    default: undefined,
  },
  format: {
    type: Function,
    default: (val) => val.toFixed(2),
  },
  compact: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:modelValue', 'change']);

const inputRef = ref(null);
const displayValue = ref(formatValueFromProps(props.modelValue));

// 格式化显示值
function formatValueFromProps(value) {
  if (value === undefined || value === null || isNaN(value)) return '0';
  const stepStr = props.step.toString();
  const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
  return value.toFixed(decimalPlaces);
}

const formatValue = computed(() => props.format(props.modelValue));

// 解析并限制数值范围
function parseAndClamp(value) {
  let num = parseFloat(value);
  if (isNaN(num)) {
    const fallback = props.min !== undefined && props.min > -Infinity ? props.min : 0;
    return fallback;
  }

  if (props.min !== undefined && num < props.min) num = props.min;
  if (props.max !== undefined && num > props.max) num = props.max;

  const stepped = Math.round(num / props.step) * props.step;
  return parseFloat(stepped.toFixed(10));
}

// 处理数字输入
const handleNumberInput = (e) => {
  let rawValue = e.target.value;

  if (
    rawValue === '' ||
    rawValue === '-' ||
    rawValue === '.' ||
    rawValue === '-.' ||
    rawValue === '-0'
  ) {
    displayValue.value = rawValue;
    return;
  }

  const regex = /^-?\d*\.?\d*$/;
  if (regex.test(rawValue)) {
    displayValue.value = rawValue;

    const numValue = parseAndClamp(rawValue);
    if (!isNaN(numValue)) {
      emit('update:modelValue', numValue);
    }
  }
};

// 处理失焦
const handleBlur = () => {
  let numValue = parseAndClamp(displayValue.value);

  if (isNaN(numValue)) {
    numValue = props.min !== undefined && props.min > -Infinity ? props.min : 0;
  }

  if (props.min !== undefined && numValue < props.min) numValue = props.min;
  if (props.max !== undefined && numValue > props.max) numValue = props.max;

  const stepped = Math.round(numValue / props.step) * props.step;
  const finalValue = parseFloat(stepped.toFixed(10));

  const stepStr = props.step.toString();
  const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
  displayValue.value = finalValue.toFixed(decimalPlaces);

  emit('update:modelValue', finalValue);
  emit('change', finalValue);
};

// 处理键盘事件
const handleKeydown = (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    handleBlur();
    inputRef.value?.blur();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    increment();
  } else if (e.key === 'ArrowDown') {
    e.preventDefault();
    decrement();
  }
};

// 增加数值
function increment() {
  let current = parseFloat(displayValue.value);
  if (isNaN(current)) current = props.modelValue;
  let newValue = current + props.step;

  if (props.max !== undefined && newValue > props.max) newValue = props.max;
  if (props.min !== undefined && newValue < props.min) newValue = props.min;

  newValue = parseFloat(newValue.toFixed(10));

  const stepStr = props.step.toString();
  const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
  displayValue.value = newValue.toFixed(decimalPlaces);

  emit('update:modelValue', newValue);
  emit('change', newValue);
}

// 减少数值
function decrement() {
  let current = parseFloat(displayValue.value);
  if (isNaN(current)) current = props.modelValue;
  let newValue = current - props.step;

  if (props.max !== undefined && newValue > props.max) newValue = props.max;
  if (props.min !== undefined && newValue < props.min) newValue = props.min;

  newValue = parseFloat(newValue.toFixed(10));

  const stepStr = props.step.toString();
  const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
  displayValue.value = newValue.toFixed(decimalPlaces);

  emit('update:modelValue', newValue);
  emit('change', newValue);
}

// 监听外部 modelValue 变化
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal !== undefined && newVal !== null && !isNaN(newVal)) {
      const stepStr = props.step.toString();
      const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
      const newDisplayValue = newVal.toFixed(decimalPlaces);
      if (displayValue.value !== newDisplayValue) {
        displayValue.value = newDisplayValue;
      }
    }
  }
);

// 监听 step 变化
watch(
  () => props.step,
  () => {
    const stepStr = props.step.toString();
    const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
    displayValue.value = props.modelValue.toFixed(decimalPlaces);
  }
);
</script>

<style scoped>
.number-input-slider {
  container-type: inline-size;
}

@container (max-width: 9rem) {
  .number-input-row {
    gap: 0.25rem;
  }

  .number-input-value {
    display: none;
  }
}

input[type='text']::-webkit-outer-spin-button,
input[type='text']::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
