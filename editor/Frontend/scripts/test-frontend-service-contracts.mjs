import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, '..');
const srcRoot = path.join(frontendRoot, 'src');
const bridgePath = path.join(srcRoot, 'utils', 'bridge.js');
const bridge = fs.readFileSync(bridgePath, 'utf8');

const serviceNames = [
  'sceneService',
  'projectService',
  'appService',
  'aiService',
  'aiClient',
  'lanChatService',
  'scriptingService',
  'projectLauncherService',
  'fileService',
  'logService',
  'resourceService',
  'projectSettingsService',
  'networkService',
];

function findMatchingBrace(source, openIndex) {
  let depth = 0;
  for (let i = openIndex; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === '{') depth += 1;
    if (ch === '}') {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  throw new Error(`Cannot find matching brace at ${openIndex}`);
}

function exportedMethods(serviceName) {
  const declaration = `export const ${serviceName} =`;
  const start = bridge.indexOf(declaration);
  if (start === -1) {
    throw new Error(`Missing service export: ${serviceName}`);
  }
  const open = bridge.indexOf('{', start);
  const close = findMatchingBrace(bridge, open);
  const body = bridge.slice(open + 1, close);
  return new Set([...body.matchAll(/^\s*([A-Za-z_$][\w$]*)\s*:/gm)].map((match) => match[1]));
}

function listSourceFiles(dir) {
  const result = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      result.push(...listSourceFiles(fullPath));
    } else if (/\.(js|vue|ts)$/.test(entry.name) && fullPath !== bridgePath) {
      result.push(fullPath);
    }
  }
  return result;
}

const serviceMethods = new Map(serviceNames.map((name) => [name, exportedMethods(name)]));
const failures = [];
const usagePattern = new RegExp(`\\b(${serviceNames.join('|')})\\.([A-Za-z_$][\\w$]*)\\b`, 'g');
const directCefFailures = [];
const forbiddenBridgeExports = ['callDockFunction'];
const forbiddenFrontendMarkers = [
  '__coronaFocusPoseResult',
  'window.showLoading',
  'window.updateLoading',
  'window.hideLoading',
  'window.applyCameraPose',
  'window.addTab',
  'window.renameTab',
  'window.onFragmentChanged',
  'window.onSceneTreeChanged',
];
const forbiddenFrontendFailures = [];

for (const file of listSourceFiles(srcRoot)) {
  const source = fs.readFileSync(file, 'utf8');
  for (const match of source.matchAll(usagePattern)) {
    const [, serviceName, methodName] = match;
    if (!serviceMethods.get(serviceName)?.has(methodName)) {
      failures.push(`${path.relative(frontendRoot, file)} uses ${serviceName}.${methodName}, but bridge.js does not export it`);
    }
  }

  for (const match of source.matchAll(/Bridge\.callCEF\(/g)) {
    const line = source.slice(0, match.index).split(/\r?\n/).length;
    directCefFailures.push(`${path.relative(frontendRoot, file)}:${line} calls Bridge.callCEF directly`);
  }

  for (const marker of forbiddenFrontendMarkers) {
    const index = source.indexOf(marker);
    if (index !== -1) {
      const line = source.slice(0, index).split(/\r?\n/).length;
      forbiddenFrontendFailures.push(`${path.relative(frontendRoot, file)}:${line} contains forbidden compatibility marker ${marker}`);
    }
  }
}

if (failures.length > 0) {
  throw new Error(`Frontend service contract violations:\n${failures.join('\n')}`);
}

if (directCefFailures.length > 0) {
  throw new Error(`Direct CEF calls outside bridge.js are not allowed:\n${directCefFailures.join('\n')}`);
}

const forbiddenBridgeFailures = forbiddenBridgeExports.filter((name) =>
  new RegExp(`\\b${name}\\s*:`).test(bridge)
);
if (forbiddenBridgeFailures.length > 0) {
  throw new Error(`Forbidden bridge compatibility exports found: ${forbiddenBridgeFailures.join(', ')}`);
}

if (forbiddenFrontendFailures.length > 0) {
  throw new Error(`Forbidden frontend compatibility markers found:\n${forbiddenFrontendFailures.join('\n')}`);
}

console.log('[OK] Frontend service calls match bridge.js exports');
