import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseJavaScript } from '@babel/parser';
import { parse as parseVueSfc } from '@vue/compiler-sfc';
import zhCN from '../src/i18n/messages/zh-CN.js';
import enUS from '../src/i18n/messages/en-US.js';
import { DOM_TEXT_TRANSLATIONS } from '../src/i18n/domTranslator.js';

const scriptsDir = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(scriptsDir, '../src');
const cjkPattern = /[\u3400-\u9fff]/;

function flatten(value, prefix = '', output = {}) {
  for (const [key, entry] of Object.entries(value || {})) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (entry && typeof entry === 'object' && !Array.isArray(entry)) {
      flatten(entry, fullKey, output);
    } else {
      output[fullKey] = entry;
    }
  }
  return output;
}

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(fullPath) : [fullPath];
  });
}

function normalizePlaceholderShape(value) {
  return value.replace(/\{[^{}]+\}/g, '{}');
}

function collectRuntimeVueText(filePath) {
  const source = fs.readFileSync(filePath, 'utf8');
  const { descriptor } = parseVueSfc(source, { filename: filePath });
  const entries = [];
  const nativeDialogs = [];
  const nativeDialogNames = new Set(['alert', 'confirm', 'prompt']);
  const translatorNames = new Set(['t', 'translate', 'translateUiText']);

  function containsChineseLiteral(node) {
    if (!node || typeof node !== 'object') return false;
    if (node.type === 'StringLiteral') return cjkPattern.test(node.value);
    if (node.type === 'TemplateElement') return cjkPattern.test(node.value.cooked || '');
    return Object.entries(node).some(([key, value]) => {
      if (['loc', 'start', 'end', 'extra'].includes(key)) return false;
      if (Array.isArray(value)) return value.some(containsChineseLiteral);
      return containsChineseLiteral(value);
    });
  }

  function isTranslatedExpression(node) {
    if (!node || node.type !== 'CallExpression') return false;
    if (node.callee?.type === 'Identifier') return translatorNames.has(node.callee.name);
    return node.callee?.type === 'MemberExpression' && node.callee.property?.name === '$t';
  }

  function visit(node, lineOffset) {
    if (!node || typeof node !== 'object') return;

    if (
      node.type === 'CallExpression' &&
      node.callee?.type === 'Identifier' &&
      nativeDialogNames.has(node.callee.name) &&
      containsChineseLiteral(node.arguments?.[0]) &&
      !isTranslatedExpression(node.arguments?.[0])
    ) {
      nativeDialogs.push({
        line: lineOffset + (node.loc?.start.line || 1),
        dialog: node.callee.name,
      });
    }

    if (node.type === 'StringLiteral' && cjkPattern.test(node.value)) {
      entries.push({
        line: lineOffset + (node.loc?.start.line || 1),
        text: node.value,
        template: false,
      });
    } else if (node.type === 'TemplateLiteral') {
      const text = node.quasis.map((quasi) => quasi.value.cooked || '').join('{}');
      if (cjkPattern.test(text)) {
        entries.push({
          line: lineOffset + (node.loc?.start.line || 1),
          text,
          template: true,
        });
      }
    }

    for (const [key, value] of Object.entries(node)) {
      if (['loc', 'start', 'end', 'extra'].includes(key)) continue;
      if (Array.isArray(value)) {
        for (const child of value) visit(child, lineOffset);
      } else if (value && typeof value === 'object') {
        visit(value, lineOffset);
      }
    }
  }

  for (const block of [descriptor.script, descriptor.scriptSetup]) {
    if (!block?.content) continue;
    const ast = parseJavaScript(block.content, {
      sourceType: 'module',
      plugins: ['jsx', 'typescript', 'topLevelAwait', 'optionalChaining'],
    });
    visit(ast, Math.max(0, (block.loc?.start.line || 1) - 1));
  }

  return { entries, nativeDialogs };
}

function collectStaticVueText(filePath) {
  const source = fs.readFileSync(filePath, 'utf8');
  const template = source.match(/<template>([\s\S]*?)<\/template>/)?.[1] || '';
  const withoutComments = template.replace(/<!--[\s\S]*?-->/g, '');
  const entries = [];

  for (const match of withoutComments.matchAll(/>([^<>{}]*[\u3400-\u9fff][^<>{}]*)</g)) {
    const text = match[1].trim();
    if (text) entries.push(text);
  }

  const attributePattern =
    /(?:^|\s)(?:title|placeholder|aria-label|alt)="([^"{}]*[\u3400-\u9fff][^"]*)"/gm;
  for (const match of withoutComments.matchAll(attributePattern)) {
    const text = match[1].trim();
    if (text) entries.push(text);
  }

  return entries;
}

const zh = flatten(zhCN);
const en = flatten(enUS);
const missingInEnglish = Object.keys(zh).filter((key) => !(key in en));
const missingInChinese = Object.keys(en).filter((key) => !(key in zh));
const intentionalSameTranslations = new Set(['locale.zhCN']);
const untranslatedEnglish = Object.keys(zh).filter(
  (key) =>
    cjkPattern.test(String(zh[key])) && zh[key] === en[key] && !intentionalSameTranslations.has(key)
);

const missingDomTranslations = [];
const missingRuntimeTranslations = [];
const untranslatedNativeDialogs = [];
const translationShapes = new Set(
  Object.keys(DOM_TEXT_TRANSLATIONS).map(normalizePlaceholderShape)
);
for (const filePath of walk(srcDir).filter((file) => file.endsWith('.vue'))) {
  const relativeFile = path.relative(srcDir, filePath).replaceAll('\\', '/');
  for (const text of collectStaticVueText(filePath)) {
    if (!Object.hasOwn(DOM_TEXT_TRANSLATIONS, text)) {
      missingDomTranslations.push({ file: relativeFile, text });
    }
  }
  const runtimeText = collectRuntimeVueText(filePath);
  for (const entry of runtimeText.entries) {
    const translated = entry.template
      ? translationShapes.has(normalizePlaceholderShape(entry.text))
      : Object.hasOwn(DOM_TEXT_TRANSLATIONS, entry.text);
    if (!translated) {
      missingRuntimeTranslations.push({
        file: relativeFile,
        line: entry.line,
        text: entry.text,
      });
    }
  }
  for (const dialog of runtimeText.nativeDialogs) {
    untranslatedNativeDialogs.push({ file: relativeFile, ...dialog });
  }
}

const uniqueDomGaps = [
  ...new Map(
    missingDomTranslations.map((entry) => [`${entry.file}\n${entry.text}`, entry])
  ).values(),
];

if (
  missingInEnglish.length ||
  missingInChinese.length ||
  untranslatedEnglish.length ||
  uniqueDomGaps.length ||
  missingRuntimeTranslations.length ||
  untranslatedNativeDialogs.length
) {
  console.error(
    JSON.stringify(
      {
        missingInEnglish,
        missingInChinese,
        untranslatedEnglish,
        missingDomTranslations: uniqueDomGaps,
        missingRuntimeTranslations,
        untranslatedNativeDialogs,
      },
      null,
      2
    )
  );
  process.exitCode = 1;
} else {
  console.log(
    `i18n check passed: ${Object.keys(zh).length} locale keys and ` +
      `${Object.keys(DOM_TEXT_TRANSLATIONS).length} DOM translations.`
  );
}
