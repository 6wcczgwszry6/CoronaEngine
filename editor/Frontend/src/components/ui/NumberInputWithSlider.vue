<!-- components/ui/NumberInputWithSlider.vue -->
<template>
  <div class="flex flex-col gap-1 w-full">
    <div class="flex items-center gap-2 w-full">
      <input
        ref="inputRef"
        type="text"
        :value="displayValue"
        :step="step"
        class="flex-1 bg-[#1a1a1a] text-[#e0e0e0] text-[10px] rounded px-2 py-0.5 outline-none border border-[#3c3c3c] focus:border-[#84a65b]"
        :style="{ textAlign: 'right' }"
        @input="handleNumberInput"
        @blur="handleBlur"
        @keydown="handleKeydown"
      />
      <span class="text-[#84a65b] text-[9px] min-w-[35px] text-right font-mono">
        {{ formatValue }}
      </span>
    </div>
    <div class="w-full px-0">
      <input
        type="range"
        :value="modelValue"
        :step="step"
        :min="min !== undefined ? min : getDefaultMin()"
        :max="max !== undefined ? max : getDefaultMax()"
        class="w-full h-1.5 rounded-lg appearance-none cursor-pointer"
        :class="sliderClass"
        @input="handleSliderInput"
        @change="handleSliderChange"
      />
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
});

const emit = defineEmits(['update:modelValue', 'change']);

const inputRef = ref(null);
const displayValue = ref(formatValueFromProps(props.modelValue));

// 动态计算滑块样式类
const sliderClass = computed(() => {
  // 根据是否在范围内添加不同样式
  const val = props.modelValue;
  const minVal = props.min !== undefined ? props.min : getDefaultMin();
  const maxVal = props.max !== undefined ? props.max : getDefaultMax();
  const percent = ((val - minVal) / (maxVal - minVal)) * 100;

  return {
    'slider-default': true,
    'slider-highlight': true,
  };
});

// 格式化显示值
function formatValueFromProps(value) {
  if (value === undefined || value === null || isNaN(value)) return '0';
  const stepStr = props.step.toString();
  const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
  return value.toFixed(decimalPlaces);
}

const formatValue = computed(() => props.format(props.modelValue));

const getDefaultMin = () => {
  if (props.step >= 1) return -100;
  if (props.step >= 0.1) return -10;
  return -1;
};

const getDefaultMax = () => {
  if (props.step >= 1) return 100;
  if (props.step >= 0.1) return 10;
  return 1;
};

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

const handleSliderInput = (e) => {
  let value = parseFloat(e.target.value);
  if (isNaN(value)) return;

  const stepped = Math.round(value / props.step) * props.step;
  const finalValue = parseFloat(stepped.toFixed(10));

  emit('update:modelValue', finalValue);

  const stepStr = props.step.toString();
  const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
  displayValue.value = finalValue.toFixed(decimalPlaces);
};

const handleSliderChange = (e) => {
  let value = parseFloat(e.target.value);
  if (isNaN(value)) return;

  const stepped = Math.round(value / props.step) * props.step;
  const finalValue = parseFloat(stepped.toFixed(10));

  emit('update:modelValue', finalValue);
  emit('change', finalValue);

  const stepStr = props.step.toString();
  const decimalPlaces = stepStr.includes('.') ? stepStr.split('.')[1].length : 2;
  displayValue.value = finalValue.toFixed(decimalPlaces);
};

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
/* 滑块容器确保宽度一致 */
input[type='range'] {
  -webkit-appearance: none;
  background: #3c3c3c;
  border-radius: 4px;
}

input[type='range']:focus {
  outline: none;
}

/* 滑块轨道 - 更明显的颜色 */
input[type='range']::-webkit-slider-runnable-track {
  width: 100%;
  height: 4px;
  background: linear-gradient(
    90deg,
    #84a65b 0%,
    #84a65b var(--fill-percent, 0%),
    #3c3c3c var(--fill-percent, 0%),
    #3c3c3c 100%
  );
  border-radius: 4px;
}

/* 滑块按钮 - 更明显 */
input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #84a65b;
  cursor: pointer;
  border: 2px solid #e0e0e0;
  margin-top: -5px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: all 0.1s ease;
}

input[type='range']::-webkit-slider-thumb:hover {
  background: #a0c47a;
  transform: scale(1.1);
  border-color: #ffffff;
}

/* Firefox 支持 */
input[type='range']::-moz-range-track {
  width: 100%;
  height: 4px;
  background: #3c3c3c;
  border-radius: 4px;
}

input[type='range']::-moz-range-progress {
  background: #84a65b;
  height: 4px;
  border-radius: 4px;
}

input[type='range']::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #84a65b;
  cursor: pointer;
  border: 2px solid #e0e0e0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

input[type='range']::-moz-range-thumb:hover {
  background: #a0c47a;
  transform: scale(1.1);
}

/* Edge/IE 支持 */
input[type='range']::-ms-track {
  width: 100%;
  height: 4px;
  background: transparent;
  border-color: transparent;
  color: transparent;
}

input[type='range']::-ms-fill-lower {
  background: #84a65b;
  border-radius: 4px;
}

input[type='range']::-ms-fill-upper {
  background: #3c3c3c;
  border-radius: 4px;
}

input[type='range']::-ms-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #84a65b;
  cursor: pointer;
  border: 2px solid #e0e0e0;
  margin-top: 0;
}

input[type='text']::-webkit-outer-spin-button,
input[type='text']::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
