<template>
  <div class="start-screen-root">
    <!-- Three.js 3D 粒子背景 -->
    <div ref="canvasContainer" class="canvas-container"></div>

    <!-- 标题 + 导航按钮（用 GSAP 定位，初始居中，点击后左移） -->
    <div ref="contentWrapper" class="start-screen-content">
      <div class="main-title">CORONA ENGINE</div>
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
    <div v-if="showPanel" class="page-panel" :class="{ visible: panelVisible }">
      <div class="page-panel-body">
        <component :is="pageComponent" />
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
  const d = 0.8;
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
const handleNavClick = (id) => {
  // 退出按钮
  if (id === 'panel-exit') {
    animateParticles(id);
    activeNav.value = id;
    setTimeout(() => appService.closeProcess(), 1000);
    return;
  }

  // 点击已激活的面板 → 关闭
  if (activePage.value === id && showPanel.value) {
    handleBack();
    return;
  }

  activeNav.value = id;
  animateParticles(id);

  // **首次点击**：菜单从中央滑到左侧（模仿 HTML 效果）
  if (!hasInteracted) {
    hasInteracted = true;
    gsap.to(contentWrapper.value, {
      left: '2vw',
      xPercent: 0,
      scale: 0.75,
      duration: 1.2,
      ease: 'power3.inOut',
    });
  }

  // 展开右侧面板
  setTimeout(() => {
    activePage.value = id;
    pageComponent.value = pageMap[id].component;
    showPanel.value = true;
    nextTick(() => {
      requestAnimationFrame(() => {
        panelVisible.value = true;
      });
    });
  }, hasInteracted ? 0 : 500);
};

const handleBack = () => {
  panelVisible.value = false;

  // 面板收起后才显示返回箭头并重置状态
  setTimeout(() => {
    showPanel.value = false;
    activePage.value = null;
    activeNav.value = null;
    pageComponent.value = null;

    gsap.to(contentWrapper.value, {
      left: '50%',
      xPercent: -50,
      scale: 1,
      duration: 0.8,
      ease: 'power3.inOut',
    });

    hasInteracted = false;
  }, 400);
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
  const count = 10000;
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
    size: 0.6,
    color: 0x66aaff,
    map: texture,
    blending: THREE.AdditiveBlending,
    transparent: true,
    opacity: 0.8,
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
    particleSystem.rotation.y += 0.0008;
    camera.position.x += (mouseX * 0.015 - camera.position.x) * 0.05;
    camera.position.y += (-mouseY * 0.015 - camera.position.y) * 0.05;
    camera.lookAt(scene.position);
    particleSystem.position.y = Math.sin(elapsed * 0.4) * 2.5;
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
  // GSAP 初始居中定位
  gsap.set(contentWrapper.value, {
    left: '50%',
    top: '50%',
    xPercent: -50,
    yPercent: -50,
    scale: 1,
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
  gap: 40px;
  z-index: 10;
  pointer-events: none;
  transform-origin: center center;
}

.main-title {
  font-size: 4.5rem;
  letter-spacing: 12px;
  font-weight: 800;
  text-transform: uppercase;
  white-space: nowrap;
  background: linear-gradient(90deg, #ffffff, #66aaff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 40px rgba(102, 170, 255, 0.3);
}

.nav-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 300px;
  pointer-events: auto;
}

.nav-btn {
  background: rgba(0, 0, 0, 0.35);
  border: none;
  border-left: 4px solid rgba(255, 255, 255, 0.08);
  color: #999;
  font-size: 1.5rem;
  text-align: left;
  padding: 18px 30px;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 3px;
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

/* 左侧返回箭头 */
.nav-back-wrapper {
  pointer-events: auto;
  margin-top: 8px;
}

.nav-back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.05);
  color: #aaa;
  cursor: pointer;
  transition: all 0.25s ease;
}

.nav-back-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

/* ——— 右侧页面面板 ——— */
.page-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 78vw;
  height: 100vh;
  z-index: 30;
  background: rgba(5, 5, 5, 0.92);
  backdrop-filter: blur(4px);
  transform: translateX(100%);
  transition: transform 0.6s cubic-bezier(0.25, 1, 0.5, 1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-panel.visible {
  transform: translateX(0);
}

.page-panel-body {
  flex: 1;
  overflow: hidden;
}
</style>
