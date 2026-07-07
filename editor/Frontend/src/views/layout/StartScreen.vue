<template>
  <div class="start-screen-root">
    <div ref="canvasContainer" class="canvas-container"></div>

    <!-- 标题 + 导航按钮 -->
    <div ref="contentWrapper" class="start-screen-content">
      <div class="main-title">CORONA<br>ENGINE</div>
      <div ref="navContainer" class="nav-container">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="nav-btn"
          :class="{ active: activeNav === item.id }"
          @click="handleNavClick(item.id)"
        >
          {{ t(item.label) }}
        </button>
      </div>
      <div v-if="showPanel" class="nav-back-wrapper">
        <button class="nav-back-btn" @click="handleBack">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
      </div>
    </div>

    <!-- 右侧页面面板 -->
    <div v-if="showPanel" ref="panelRef" class="page-panel" :class="{ visible: panelVisible }">
      <div class="page-panel-body">
        <!-- 退出确认 -->
        <div v-if="activePage === 'panel-exit'" key="panel-exit" class="exit-panel-content">
          <div class="exit-panel-icon">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </div>
          <h2 class="exit-panel-title">断开连接</h2>
          <p class="exit-panel-desc">切断与 Corona 系统的连接后，所有未保存的宇宙演化进程将在后台处于休眠状态。</p>
          <div class="exit-panel-stats">
            <div class="exit-stat"><span class="exit-stat-label">进行中任务</span><span class="exit-stat-value">0</span></div>
            <div class="exit-stat"><span class="exit-stat-label">活跃宇宙</span><span class="exit-stat-value">1</span></div>
          </div>
          <div class="exit-panel-actions">
            <button class="exit-action cancel" @click="handleBack">取消</button>
            <button class="exit-action confirm" @click="confirmExit">确认离开</button>
          </div>
        </div>
        <!-- 其他页面内容切换带淡入淡出 -->
        <Transition v-else name="page-fade" mode="out-in">
          <component :is="pageComponent" :key="activePage" />
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, shallowRef, nextTick, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { appService } from '@/utils/bridge.js';
import * as THREE from 'three';
import gsap from 'gsap';

import NewGame from './NewGame.vue';
import RecentGames from './RecentGames.vue';
import JoinGame from './JoinGame.vue';

const { t } = useI18n();
const canvasContainer = ref(null);
const contentWrapper = ref(null);
const navContainer = ref(null);
const panelRef = ref(null);
const activeNav = ref(null);

const showPanel = ref(false);
const panelVisible = ref(false);
const activePage = ref(null);
const pageComponent = shallowRef(null);

const pageMap = {
  'panel-new':      { component: NewGame,     name: 'start.newGame' },
  'panel-continue': { component: RecentGames, name: 'start.continueGame' },
  'panel-multi':    { component: JoinGame,    name: 'start.joinGame' },
};

const navItems = [
  { id: 'panel-new',      label: 'start.newGame',      page: true },
  { id: 'panel-continue', label: 'start.continueGame', page: true },
  { id: 'panel-multi',    label: 'start.joinGame',     page: true },
  { id: 'panel-exit',     label: 'start.leaveGame',    page: false },
];

// ——— Three.js 状态 ———
let scene, camera, renderer, particleSystem, clock;
let mouseX = 0, mouseY = 0;
let animationFrameId = null;
let hasInteracted = false;

// ——— 粒子颜色/相机动画 ———
const animateParticles = (id) => {
  const d = 0.7;
  switch (id) {
    case 'panel-new':
      gsap.to(particleSystem.material.color, { r: 0.4, g: 0.66, b: 1, duration: d });
      gsap.to(camera.position, { z: 80, duration: d, ease: 'power2.out' });
      break;
    case 'panel-continue':
      gsap.to(particleSystem.material.color, { r: 0.1, g: 0.8, b: 0.4, duration: d });
      gsap.to(camera.position, { z: 42, duration: d, ease: 'power2.inOut' });
      break;
    case 'panel-multi':
      gsap.to(particleSystem.material.color, { r: 1.0, g: 0.4, b: 0.1, duration: d });
      gsap.to(camera.position, { z: 65, duration: d, ease: 'power2.out' });
      break;
    case 'panel-exit':
      gsap.to(particleSystem.material.color, { r: 0.8, g: 0.1, b: 0.2, duration: d });
      gsap.to(camera.position, { z: 140, duration: d, ease: 'power3.inOut' });
      break;
  }
};

// ——— 导航处理 ———
const openPanelWithAnimation = async (id, component) => {
  activePage.value = id;
  pageComponent.value = component;
  showPanel.value = true;
  panelVisible.value = true;

  await nextTick();
  // GSAP 驱动面板滑入，与菜单动画重叠
  gsap.fromTo(
    panelRef.value,
    { x: '105%' },
    { x: '0%', duration: 0.5, ease: 'power3.out', delay: 0.15 }
  );
};

const handleNavClick = async (id) => {
  // 退出：跟其他页面一样展开面板
  if (id === 'panel-exit') {
    animateParticles(id);
    activeNav.value = id;

    if (!hasInteracted) {
      hasInteracted = true;
      gsap.to(contentWrapper.value, {
        left: '2vw', xPercent: 0, scale: 0.72,
        duration: 0.8, ease: 'power3.inOut',
      });
    }
    await openPanelWithAnimation('panel-exit', null);
    return;
  }

  // 再次点击已激活的页面 → 关闭
  if (activePage.value === id && showPanel.value) {
    handleBack();
    return;
  }

  activeNav.value = id;
  animateParticles(id);

  if (!hasInteracted) {
    hasInteracted = true;
    gsap.to(contentWrapper.value, {
      left: '2vw', xPercent: 0, scale: 0.72,
      duration: 0.8, ease: 'power3.inOut',
    });
  }

  await openPanelWithAnimation(id, pageMap[id].component);
};

const handleBack = () => {
  if (!panelRef.value) return;
  panelVisible.value = false;

  gsap.to(panelRef.value, {
    x: '105%',
    duration: 0.3,
    ease: 'power2.in',
    onComplete: () => {
      showPanel.value = false;
      activePage.value = null;
      activeNav.value = null;
      pageComponent.value = null;

      gsap.to(contentWrapper.value, {
        left: '50%', xPercent: -50, scale: 1,
        duration: 0.55, ease: 'power3.inOut',
      });
      hasInteracted = false;
    },
  });
};

const confirmExit = () => {
  if (!panelRef.value) return;
  panelVisible.value = false;

  gsap.to(panelRef.value, {
    x: '105%', duration: 0.3, ease: 'power2.in',
    onComplete: () => {
      showPanel.value = false;
      appService.closeProcess();
    },
  });
};

// ——— Three.js 初始化 ———
const initThree = () => {
  const container = canvasContainer.value;
  if (!container) return;

  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x050505, 0.003);

  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 80;

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const geometry = new THREE.BufferGeometry();
  const count = 8000;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count * 3; i += 3) {
    const r = 100 * Math.cbrt(Math.random());
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i]     = r * Math.sin(phi) * Math.cos(theta);
    positions[i + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i + 2] = r * Math.cos(phi);
  }
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  const cvs = document.createElement('canvas');
  cvs.width = 32; cvs.height = 32;
  const ctx = cvs.getContext('2d');
  ctx.beginPath();
  ctx.arc(16, 16, 14, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.fill();
  const texture = new THREE.CanvasTexture(cvs);

  const material = new THREE.PointsMaterial({
    size: 0.55,
    color: 0x66aaff,
    map: texture,
    blending: THREE.AdditiveBlending,
    transparent: true,
    opacity: 0.7,
    depthWrite: false,
  });

  particleSystem = new THREE.Points(geometry, material);
  scene.add(particleSystem);

  clock = new THREE.Clock();

  const onMouseMove = (e) => {
    mouseX = e.clientX - window.innerWidth / 2;
    mouseY = e.clientY - window.innerHeight / 2;
  };
  document.addEventListener('mousemove', onMouseMove);

  const onResize = () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  };
  window.addEventListener('resize', onResize);

  const animate = () => {
    animationFrameId = requestAnimationFrame(animate);
    const elapsed = clock.getElapsedTime();
    particleSystem.rotation.y += 0.0006;
    camera.position.x += (mouseX * 0.012 - camera.position.x) * 0.04;
    camera.position.y += (-mouseY * 0.012 - camera.position.y) * 0.04;
    camera.lookAt(scene.position);
    particleSystem.position.y = Math.sin(elapsed * 0.3) * 2;
    renderer.render(scene, camera);
  };
  animate();

  return () => {
    document.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('resize', onResize);
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    renderer.dispose();
    if (container.contains(renderer.domElement)) {
      container.removeChild(renderer.domElement);
    }
  };
};

let cleanupThree = null;

onMounted(() => {
  cleanupThree = initThree();
  gsap.set(contentWrapper.value, {
    left: '50%', top: '50%', xPercent: -50, yPercent: -50, scale: 1,
  });
});

onUnmounted(() => {
  if (cleanupThree) cleanupThree();
});
</script>

<style scoped>
.start-screen-root {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  background-color: #050505;
  overflow: hidden;
}

.canvas-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

/* ——— 内容区（标题 + 按钮），由 GSAP 控制定位 ——— */
.start-screen-content {
  position: fixed;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 32px;
  z-index: 10;
  pointer-events: none;
  transform-origin: center center;
  will-change: transform;
}

.main-title {
  font-size: 3.2rem;
  letter-spacing: 12px;
  font-weight: 800;
  text-transform: uppercase;
  line-height: 1.15;
  background: linear-gradient(90deg, #ffffff, #66aaff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 36px rgba(102, 170, 255, 0.25);
}

.nav-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 260px;
  pointer-events: auto;
}

.nav-btn {
  background: rgba(0, 0, 0, 0.35);
  border: none;
  border-left: 4px solid rgba(255, 255, 255, 0.08);
  color: #999;
  font-size: 1.2rem;
  text-align: left;
  padding: 14px 24px;
  cursor: pointer;
  transition: all 0.25s ease;
  letter-spacing: 2px;
  backdrop-filter: blur(5px);
  border-radius: 0 6px 6px 0;
}

.nav-btn:hover {
  color: #fff;
  border-left-color: rgba(255, 255, 255, 0.5);
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.07) 0%, transparent 100%);
}

.nav-btn.active {
  color: #fff;
  border-left-color: #66aaff;
  background: linear-gradient(90deg, rgba(102, 170, 255, 0.12) 0%, transparent 100%);
  text-shadow: 0 0 12px rgba(102, 170, 255, 0.4);
}

.nav-back-wrapper {
  pointer-events: auto;
  margin-top: 4px;
}

.nav-back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #aaa;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-back-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* ——— 右侧页面面板（更小，浮出效果） ——— */
.page-panel {
  position: fixed;
  top: 12vh;
  right: 3vw;
  width: 56vw;
  height: 76vh;
  z-index: 30;
  background: rgba(5, 5, 5, 0.92);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: -8px 0 40px rgba(0, 0, 0, 0.4);
  will-change: transform;
}

.page-panel-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 页面内容切换淡入淡出 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease;
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

/* ——— 退出确认面板内容 ——— */
.exit-panel-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 32px;
  text-align: center;
}

.exit-panel-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(255, 68, 68, 0.08);
  color: #ff4444;
  margin-bottom: 6px;
}

.exit-panel-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 3px;
  margin: 0;
}

.exit-panel-desc {
  font-size: 0.9rem;
  line-height: 1.6;
  color: #999;
  max-width: 420px;
  margin: 0;
}

.exit-panel-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin: 12px 0 4px;
  padding: 14px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.exit-stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.exit-stat-label {
  font-size: 0.7rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.exit-stat-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: #fff;
}

.exit-panel-actions {
  display: flex;
  gap: 14px;
  margin-top: 8px;
}

.exit-action {
  padding: 10px 32px;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  letter-spacing: 1px;
  border: none;
}

.exit-action.cancel {
  background: rgba(255, 255, 255, 0.06);
  color: #aaa;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.exit-action.cancel:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.exit-action.confirm {
  background: rgba(255, 68, 68, 0.12);
  color: #ff4444;
  border: 1px solid rgba(255, 68, 68, 0.25);
}

.exit-action.confirm:hover {
  background: rgba(255, 68, 68, 0.22);
  box-shadow: 0 0 20px rgba(255, 68, 68, 0.1);
}
</style>
