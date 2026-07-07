<template>
  <div class="start-screen-root">
    <div ref="canvasContainer" class="canvas-container"></div>

    <!-- 标题固定居中不动 -->
    <div class="main-title">CORONA<br>ENGINE</div>

    <!-- 导航按钮（GSAP 控制居中/左移） -->
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

    <!-- 右侧面板 -->
    <div v-if="showPanel" ref="panelRef" class="page-panel">
      <div class="page-panel-body">
        <div v-if="activePage === 'panel-exit'" key="panel-exit" class="exit-panel-content">
          <div class="exit-panel-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </div>
          <h2 class="exit-panel-title">断开连接</h2>
          <p class="exit-panel-desc">切断与 Corona 系统的连接后，所有未保存的宇宙演化进程将在后台处于休眠状态。</p>
          <div class="exit-panel-actions">
            <button class="exit-action cancel" @click="handleBack">取消</button>
            <button class="exit-action confirm" @click="confirmExit">确认离开</button>
          </div>
        </div>
        <Transition v-else name="page-fade" mode="out-in"><component :is="pageComponent" :key="activePage" />
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
const navContainer = ref(null);
const panelRef = ref(null);
const activeNav = ref(null);

const showPanel = ref(false);
const activePage = ref(null);
const pageComponent = shallowRef(null);
const hasMoved = ref(false);

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

let scene, camera, renderer, particleSystem, clock;
let mouseX = 0, mouseY = 0;
let animationFrameId = null;
let resizeTimer = null;

const animateParticles = (id) => {
  const d = 0.6;
  switch (id) {
    case 'panel-new':
      gsap.to(particleSystem.material.color, { r: 0.4, g: 0.66, b: 1, duration: d, force3D: true });
      gsap.to(particleSystem.scale, { x: 1, y: 1, z: 1, duration: d, force3D: true });
      gsap.to(camera.position, { z: 80, duration: d, ease: 'power2.out', force3D: true });
      break;
    case 'panel-continue':
      gsap.to(particleSystem.material.color, { r: 0.1, g: 0.8, b: 0.4, duration: d, force3D: true });
      gsap.to(particleSystem.scale, { x: 1, y: 1, z: 1, duration: d, force3D: true });
      gsap.to(camera.position, { z: 42, duration: d, ease: 'power2.inOut', force3D: true });
      break;
    case 'panel-multi':
      gsap.to(particleSystem.material.color, { r: 1.0, g: 0.4, b: 0.1, duration: d, force3D: true });
      gsap.to(particleSystem.scale, { x: 1, y: 1, z: 1, duration: d, force3D: true });
      gsap.to(camera.position, { z: 65, duration: d, ease: 'power2.out', force3D: true });
      break;
    case 'panel-exit':
      gsap.to(particleSystem.material.color, { r: 0.8, g: 0.1, b: 0.2, duration: d, force3D: true });
      gsap.to(particleSystem.scale, { x: 0.4, y: 0.4, z: 0.4, duration: d, ease: 'power3.inOut', force3D: true });
      gsap.to(camera.position, { z: 100, duration: d, ease: 'power3.inOut', force3D: true });
      break;
  }
};

const showAndSlidePanel = async (id, component) => {
  activePage.value = id;
  pageComponent.value = component;
  showPanel.value = true;
  await nextTick();
  gsap.fromTo(panelRef.value,
    { x: '105%' },
    { x: '0%', duration: 0.45, ease: 'power3.out', force3D: true }
  );
};

const handleNavClick = async (id) => {
  if (id === 'panel-exit') {
    animateParticles(id);
    activeNav.value = id;
    if (!hasMoved.value) {
      hasMoved.value = true;
      gsap.to(navContainer.value, {
        x: '6vw', xPercent: 0,
        duration: 0.7, ease: 'power3.inOut', force3D: true,
      });
    }
    await showAndSlidePanel('panel-exit', null);
    return;
  }

  if (activePage.value === id && showPanel.value) {
    handleBack();
    return;
  }

  activeNav.value = id;
  animateParticles(id);

  if (!hasMoved.value) {
    hasMoved.value = true;
    gsap.to(navContainer.value, {
      x: '6vw', xPercent: 0,
      duration: 0.7, ease: 'power3.inOut', force3D: true,
    });
  }

  await showAndSlidePanel(id, pageMap[id].component);
};

const handleBack = () => {
  if (!panelRef.value) return;
  gsap.to(panelRef.value, {
    x: '105%', duration: 0.25, ease: 'power2.in', force3D: true,
    onComplete: () => {
      showPanel.value = false;
      activePage.value = null;
      activeNav.value = null;
      pageComponent.value = null;

      gsap.to(navContainer.value, {
        x: '50vw', xPercent: -50,
        duration: 0.5, ease: 'power3.inOut', force3D: true,
      });
      hasMoved.value = false;
    },
  });
};

const confirmExit = () => {
  if (!panelRef.value) return;
  gsap.to(panelRef.value, {
    x: '105%', duration: 0.25, ease: 'power2.in', force3D: true,
    onComplete: () => {
      showPanel.value = false;
      appService.closeProcess();
    },
  });
};

const initThree = () => {
  const container = canvasContainer.value;
  if (!container) return;

  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x050505, 0.003);

  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 80;

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(1);
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
  cvs.width = 24; cvs.height = 24;
  const ctx = cvs.getContext('2d');
  ctx.beginPath();
  ctx.arc(12, 12, 10, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.fill();
  const texture = new THREE.CanvasTexture(cvs);

  const material = new THREE.PointsMaterial({
    size: 0.5,
    color: 0x66aaff,
    map: texture,
    blending: THREE.AdditiveBlending,
    transparent: true,
    opacity: 0.65,
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
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }, 80);
  };
  window.addEventListener('resize', onResize);

  const animate = () => {
    animationFrameId = requestAnimationFrame(animate);
    const elapsed = clock.getElapsedTime();
    particleSystem.rotation.y += 0.0004;
    particleSystem.rotation.x = Math.sin(elapsed * 0.08) * 0.015;
    camera.position.x += (mouseX * 0.012 - camera.position.x) * 0.03;
    camera.position.y += (-mouseY * 0.012 - camera.position.y) * 0.03;
    camera.lookAt(scene.position);
    renderer.render(scene, camera);
  };
  animate();

  return () => {
    document.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('resize', onResize);
    clearTimeout(resizeTimer);
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
  gsap.set(navContainer.value, {
    x: '50vw', xPercent: -50, yPercent: -50,
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
  contain: strict;
}

/* ——— 标题固定居中，不动 ——— */
.main-title {
  position: fixed;
  top: 8vh;
  left: 50%;
  transform: translateX(-50%);
  font-size: 6.5rem;
  letter-spacing: 16px;
  font-weight: 800;
  text-transform: uppercase;
  line-height: 1.12;
  text-align: center;
  background: linear-gradient(90deg, #ffffff, #66aaff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 40px rgba(102, 170, 255, 0.2);
  z-index: 40;
  pointer-events: none;
}

/* ——— 导航按钮，GSAP 驱动位置（初始居中，点击左移） ——— */
.nav-container {
  position: fixed;
  top: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22px;
  min-width: 320px;
  pointer-events: auto;
  will-change: transform;
  z-index: 10;
}

.nav-btn {
  background: rgba(0, 0, 0, 0.35);
  border: none;
  border-left: 5px solid rgba(255, 255, 255, 0.08);
  color: #999;
  font-size: 2rem;
  text-align: left;
  padding: 20px 34px;
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease;
  letter-spacing: 3px;
  backdrop-filter: blur(5px);
  border-radius: 0 8px 8px 0;
}

.nav-btn:hover {
  color: #fff;
  border-left-color: rgba(255, 255, 255, 0.5);
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.08) 0%, transparent 100%);
}

.nav-btn.active {
  color: #fff;
  border-left-color: #66aaff;
  background: linear-gradient(90deg, rgba(102, 170, 255, 0.12) 0%, transparent 100%);
  text-shadow: 0 0 14px rgba(102, 170, 255, 0.4);
}
/* ——— 右侧面板 ——— */
.page-panel {
  position: fixed;
  top: 28vh;
  right: 3vw;
  width: 44vw;
  height: 70vh;
  z-index: 30;
  background: rgba(5, 5, 5, 0.92);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 14px;
  border: 2px solid #84a65b;
  box-shadow: -8px 0 40px rgba(0, 0, 0, 0.4);
  contain: layout style paint;
}

.page-panel-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.page-panel-body :deep(.min-h-screen),
.page-panel-body :deep(.h-screen) {
  min-height: 100% !important;
  height: 100% !important;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.18s ease;
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

/* ——— 退出确认面板（字体放大） ——— */
.exit-panel-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 36px;
  text-align: center;
}

.exit-panel-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(255, 68, 68, 0.08);
  color: #ff4444;
  margin-bottom: 8px;
}

.exit-panel-title {
font-size: 2.8rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 4px;
  margin: 0;
}

.exit-panel-desc {
font-size: 1.3rem;
  line-height: 1.6;
  color: #999;
  max-width: 420px;
  margin: 0;
}









.exit-panel-actions {
  display: flex;
  gap: 16px;
  margin-top: 12px;
}

.exit-action {
padding: 14px 40px;
border-radius: 8px;
font-size: 1.15rem;
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
  box-shadow: 0 0 18px rgba(255, 68, 68, 0.1);
}
</style>












