import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..', '..', '..');
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), 'utf8');

const cefBridge = read('src/systems/ui/cef/cef_query_bridge.cpp');
const nativeRpc = read('src/systems/ui/cef/cef_native_rpc.cpp');
const coronaEditor = read('editor/CoronaCore/core/corona_editor.py');

function assertIncludes(haystack, needle, message) {
  if (!haystack.includes(needle)) {
    throw new Error(message);
  }
}

function assertNotIncludes(haystack, needle, message) {
  if (haystack.includes(needle)) {
    throw new Error(message);
  }
}

assertIncludes(
  cefBridge,
  'is_python_fallback_allowed',
  'CEF query bridge must gate Python fallback behind an explicit allowlist',
);
assertIncludes(
  nativeRpc,
  'create_world_project',
  'CEF native RPC Python fallback allowlist must keep ProjectLauncher world project creation on Python',
);
assertIncludes(
  cefBridge,
  'unsupported_python_route_json',
  'CEF query bridge must return an explicit unsupported response for non-whitelisted Python routes',
);
assertNotIncludes(
  cefBridge,
  'Py_Initialize();',
  'CEF query bridge must not initialize Python; ScriptSystem/PythonAPI owns interpreter startup',
);
assertIncludes(
  cefBridge,
  'Python backend is not initialized',
  'CEF query bridge must return a clear error if Python fallback is called before ScriptSystem initializes it',
);
assertIncludes(
  coronaEditor,
  'is_python_route_allowed',
  'CoronaEditor must expose a Python route allowlist before invoking registered plugin methods',
);
assertIncludes(
  coronaEditor,
  '"ScratchTool"',
  'ScratchTool must remain on the Python route for Blockly script execution',
);
assertIncludes(
  coronaEditor,
  '"AITool"',
  'AITool must remain on the Python route',
);
assertIncludes(
  coronaEditor,
  '"create_world_project"',
  'CoronaEditor allowlist must keep ProjectLauncher world project creation on Python',
);

console.log('[OK] CEF/Python routing policy is explicit');
