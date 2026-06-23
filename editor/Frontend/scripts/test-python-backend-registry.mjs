import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..', '..', '..');
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), 'utf8');
const exists = (relativePath) => fs.existsSync(path.join(root, relativePath));

function fail(message) {
  throw new Error(message);
}

function assertIncludes(source, needle, message) {
  if (!source.includes(needle)) fail(message);
}

function assertNotIncludes(source, needle, message) {
  if (source.includes(needle)) fail(message);
}

function assertExists(relativePath, message) {
  if (!exists(relativePath)) fail(message);
}

function assertMissing(relativePath, message) {
  if (exists(relativePath)) fail(message);
}

const loadUtils = read('editor/CoronaPlugin/utils/load_utils.py');
const pluginBase = read('editor/CoronaPlugin/core/corona_plugin_base.py');
const registry = read('editor/backend/registry.py');

assertIncludes(
  loadUtils,
  'backend.registry',
  'Python backend loading must go through the explicit backend registry',
);
assertIncludes(
  loadUtils,
  'Backend.registry',
  'Python backend loading must tolerate the existing runtime Backend package casing',
);
assertNotIncludes(
  loadUtils,
  'plugins_dir',
  'Python backend loading must not scan editor/plugins directories',
);
assertNotIncludes(
  loadUtils,
  'spec_from_file_location',
  'Python backend loading must not import arbitrary plugin main.py files',
);
assertNotIncludes(
  pluginBase,
  'CoronaEditor.register_page',
  'PluginBase.register_web must not register page-shaped Python backends',
);
assertIncludes(
  registry,
  'PYTHON_BACKEND_SERVICES',
  'Explicit Python backend registry must declare service mappings',
);
assertIncludes(
  registry,
  'class PythonBackendService',
  'Python backend registry must expose backend service proxy objects',
);
assertIncludes(
  registry,
  '"AITool"',
  'AI backend must remain explicitly registered',
);
assertIncludes(
  registry,
  '"ScratchTool"',
  'Blockly/Scratch backend must remain explicitly registered',
);
assertIncludes(
  registry,
  '_BACKEND_PACKAGE',
  'Explicit Python backend registry must derive migrated backend package names from its own package casing',
);
assertIncludes(
  registry,
  'f"{_BACKEND_PACKAGE}.blockly.main"',
  'ScratchTool backend must be registered from backend/blockly, not editor/plugins',
);
assertIncludes(
  registry,
  'f"{_BACKEND_PACKAGE}.file_system.main"',
  'FileManager backend must be registered from backend/file_system, not editor/plugins',
);
assertIncludes(
  registry,
  'f"{_BACKEND_PACKAGE}.project_settings.main"',
  'ProjectSettings backend must be registered from backend/project_settings, not editor/plugins',
);
assertNotIncludes(
  registry,
  '"LogTool"',
  'Legacy page-shaped LogTool backend must not be registered',
);
assertNotIncludes(
  registry,
  '"ResourceSearch"',
  'Legacy ResourceSearch plugin backend must not be registered',
);
assertNotIncludes(
  registry,
  '"LANChat"',
  'LANChat Python plugin backend must not be registered because C++ owns it',
);

assertExists('editor/backend/blockly/main.py', 'ScratchTool must be migrated to editor/backend/blockly');
assertExists('editor/backend/file_system/main.py', 'FileManager must be migrated to editor/backend/file_system');
assertExists('editor/backend/project_settings/main.py', 'ProjectSettings must be migrated to editor/backend/project_settings');

assertMissing('editor/plugins/ScratchTool/main.py', 'Old ScratchTool plugin backend file must be deleted');
assertMissing('editor/plugins/ProjectFileManager/main.py', 'Old ProjectFileManager plugin backend file must be deleted');
assertMissing('editor/plugins/ProjectSettings/main.py', 'Old ProjectSettings plugin backend file must be deleted');
assertMissing('editor/plugins/LogTool/main.py', 'Old LogTool page-shaped backend file must be deleted');
assertMissing('editor/plugins/LANChat/main.py', 'Old LANChat Python backend file must be deleted');
assertMissing('editor/plugins/ResourceSearch/main.py', 'Old ResourceSearch Python backend file must be deleted');

for (const movedPath of [
  'editor/backend/blockly/main.py',
  'editor/backend/file_system/main.py',
  'editor/backend/project_settings/main.py',
]) {
  const movedSource = read(movedPath);
  assertNotIncludes(
    movedSource,
    'PluginBase',
    `${movedPath} must not depend on page-shaped PluginBase`,
  );
  assertNotIncludes(
    movedSource,
    'register_web',
    `${movedPath} must not use page-shaped register_web decorators`,
  );
}

console.log('[OK] Python backend registry is explicit');
