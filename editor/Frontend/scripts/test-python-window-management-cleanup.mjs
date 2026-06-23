import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..', '..', '..');
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), 'utf8');

function fail(message) {
  throw new Error(message);
}

function assertIncludes(source, needle, message) {
  if (!source.includes(needle)) fail(message);
}

function assertNotIncludes(source, needle, message) {
  if (source.includes(needle)) fail(message);
}

const coronaEditor = read('editor/CoronaCore/core/corona_editor.py');
const editorMain = read('editor/main.py');
const cefPyBind = read('src/systems/ui/cef/cef_py_bind.cpp');
const imguiSystem = read('src/systems/ui/imgui_system.cpp');
const bridge = read('editor/Frontend/src/utils/bridge.js');
const eventBus = read('editor/Frontend/src/utils/eventBus.js');

assertNotIncludes(
  coronaEditor,
  '_main_tab_id',
  'CoronaEditor must not store frontend tab ids in Python',
);
assertNotIncludes(
  coronaEditor,
  'def reload_frontend',
  'CoronaEditor must not expose Python-side frontend reload/window management',
);
assertNotIncludes(
  editorMain,
  'create_browser_tab',
  'editor/main.py must not create frontend CEF tabs from Python',
);
assertNotIncludes(
  cefPyBind,
  'm.def("create_browser_tab"',
  'Python bindings must not expose create_browser_tab',
);
assertNotIncludes(
  cefPyBind,
  'm.def("execute_javascript"',
  'Python bindings must not expose JavaScript execution/window control',
);
assertNotIncludes(
  coronaEditor,
  'execute_javascript',
  'CoronaEditor must not call CEF JavaScript execution from Python',
);
assertNotIncludes(
  coronaEditor,
  '__coronaEmit',
  'CoronaEditor must not inject frontend event JavaScript from Python',
);
assertNotIncludes(
  coronaEditor,
  'js_call_func',
  'CoronaEditor must not keep the legacy Python-to-JS compatibility API',
);
assertNotIncludes(
  bridge,
  'start_corona_engine',
  'Frontend bridge must not call Python to start or manage frontend windows',
);
assertNotIncludes(
  eventBus,
  'Python execute_javascript',
  'Frontend event bus must not document Python JavaScript execution as a source',
);
assertIncludes(
  imguiSystem,
  'create_initial_frontend_tab',
  'C++ UI system must own initial Vue/CEF tab creation',
);

console.log('[OK] Python frontend window management is cleaned up');
