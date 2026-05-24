export function looksLikeMarkdown(text) {
  return /(^|\n)#{1,6}\s+|(^|\n)```|(^|\n)>\s+|(^|\n)\s*[-*+]\s+|(^|\n)\s*\d+\.\s+|\[[^\]]+\]\([^\s)]+\)|`[^`]+`|\*\*[^*]+\*\*|(^|\n)\|.+\|/m.test(
    text || '',
  );
}

export function parseMarkdown(text) {
  const lines = String(text || '').replace(/\r\n/g, '\n').split('\n');
  const result = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fenceMatch = line.match(/^```\s*([\w#+.-]*)\s*$/);
    if (fenceMatch) {
      const language = fenceMatch[1] || '';
      const codeLines = [];
      index += 1;
      while (index < lines.length && !lines[index].match(/^```\s*$/)) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      result.push({ type: 'code', language, text: codeLines.join('\n') });
      continue;
    }

    if (/^---+$/.test(line.trim())) {
      result.push({ type: 'hr' });
      index += 1;
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      result.push({ type: 'heading', level: heading[1].length, html: renderInline(heading[2]) });
      index += 1;
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quoteLines = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^>\s?/, ''));
        index += 1;
      }
      result.push({ type: 'blockquote', html: quoteLines.map(renderInline).join('<br>') });
      continue;
    }

    const unorderedMatch = line.match(/^\s*[-*+]\s+(.+)$/);
    if (unorderedMatch) {
      const items = [];
      while (index < lines.length) {
        const item = lines[index].match(/^\s*[-*+]\s+(.+)$/);
        if (!item) break;
        items.push(renderInline(item[1]));
        index += 1;
      }
      result.push({ type: 'ul', items });
      continue;
    }

    const orderedMatch = line.match(/^\s*\d+\.\s+(.+)$/);
    if (orderedMatch) {
      const items = [];
      while (index < lines.length) {
        const item = lines[index].match(/^\s*\d+\.\s+(.+)$/);
        if (!item) break;
        items.push(renderInline(item[1]));
        index += 1;
      }
      result.push({ type: 'ol', items });
      continue;
    }

    if (isTableStart(lines, index)) {
      const header = splitTableRow(lines[index]).map(renderInline);
      index += 2;
      const rows = [];
      while (index < lines.length && /^\s*\|.*\|\s*$/.test(lines[index])) {
        rows.push(splitTableRow(lines[index]).map(renderInline));
        index += 1;
      }
      result.push({ type: 'table', header, rows });
      continue;
    }

    const paragraphLines = [];
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines, index)) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    if (paragraphLines.length === 0) {
      paragraphLines.push(line);
      index += 1;
    }
    result.push({ type: 'paragraph', html: paragraphLines.map(renderInline).join('<br>') });
  }

  return result;
}

export function renderPlainTextBlock(text) {
  return {
    type: 'paragraph',
    html: escapeHtml(text).replace(/\n/g, '<br>'),
  };
}

function isBlockStart(lines, index) {
  const line = lines[index] || '';
  return (
    /^```/.test(line) ||
    /^#{1,6}\s+/.test(line) ||
    /^>\s?/.test(line) ||
    /^\s*[-*+]\s+/.test(line) ||
    /^\s*\d+\.\s+/.test(line) ||
    /^---+$/.test(line.trim()) ||
    isTableStart(lines, index)
  );
}

function isTableStart(lines, index) {
  return (
    /^\s*\|.*\|\s*$/.test(lines[index] || '') &&
    /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1] || '')
  );
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

function renderInline(value) {
  let html = escapeHtml(value);
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  html = html.replace(/\[([^\]]+)\]\(([^\s)]+)\)/g, (_match, label, href) => {
    const safeHref = sanitizeHref(href);
    if (!safeHref) {
      return label;
    }
    return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${label}</a>`;
  });
  return html;
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function sanitizeHref(value) {
  const href = String(value || '').trim();
  if (/^(https?:|file:)/i.test(href)) {
    return escapeHtml(href);
  }
  return '';
}