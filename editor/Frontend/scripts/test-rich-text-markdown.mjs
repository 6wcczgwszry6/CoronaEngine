import assert from 'node:assert/strict';

import {
  looksLikeMarkdown,
  parseMarkdown,
  renderPlainTextBlock,
} from '../src/utils/richTextMarkdown.js';

const blocks = parseMarkdown(`# 标题

正文 **加粗** 和 [链接](https://example.com)

| 名称 | 值 |
| --- | --- |
| A | \`1\` |

\`\`\`js
console.log('ok')
\`\`\`
`);

assert.equal(blocks[0].type, 'heading');
assert.equal(blocks[0].level, 1);
assert.match(blocks[1].html, /<strong>加粗<\/strong>/);
assert.match(blocks[1].html, /href="https:\/\/example.com"/);
assert.equal(blocks[2].type, 'table');
assert.equal(blocks[3].type, 'code');
assert.equal(blocks[3].language, 'js');

const unsafe = parseMarkdown(`<script>alert(1)</script>
[bad](javascript:alert(1))
[file](file:///D:/demo.txt)`);

assert.match(unsafe[0].html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
assert.doesNotMatch(unsafe[0].html, /<script>/);
assert.doesNotMatch(unsafe[0].html, /javascript:/);
assert.match(unsafe[0].html, /href="file:\/\/\/D:\/demo.txt"/);

const streamingFence = parseMarkdown('```cpp\nint main() {');
assert.equal(streamingFence[0].type, 'code');
assert.equal(streamingFence[0].language, 'cpp');
assert.equal(streamingFence[0].text, 'int main() {');

assert.equal(looksLikeMarkdown('普通文本'), false);
assert.equal(looksLikeMarkdown('- 列表'), true);
assert.deepEqual(renderPlainTextBlock('<b>x</b>'), {
  type: 'paragraph',
  html: '&lt;b&gt;x&lt;/b&gt;',
});

console.log('rich text markdown tests passed');