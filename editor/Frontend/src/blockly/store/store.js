import { ref, shallowRef } from 'vue';

const workspace = shallowRef(null);
const workspaceSvg = shallowRef(null);

const hasLayoutSider = ref(false);
const searchVisible = ref(false);

export function useStore() {
  return {
    workspace,
    workspaceSvg,
    hasLayoutSider,
    searchVisible,
  };
}
