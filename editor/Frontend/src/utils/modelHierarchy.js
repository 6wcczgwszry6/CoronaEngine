export const pickedNodeIdentity = (payload = {}) => {
  const nodeIndex = Number(payload?.node_index ?? payload?.nodeIndex);
  const actorName = payload?.actor_name || payload?.actorName || payload?.name || payload?.actor?.name;
  if (!actorName || !Number.isInteger(nodeIndex) || nodeIndex < 0) return null;
  return { actorName, nodeIndex };
};

export const nodeTree = (nodes = []) => {
  const byIndex = new Map(nodes.map((node) => [Number(node.node_index), { ...node, children: [] }]));
  const roots = [];
  for (const node of byIndex.values()) {
    const parent = byIndex.get(Number(node.parent_index));
    if (parent) parent.children.push(node); else roots.push(node);
  }
  return roots;
};

export const flattenLoadedNodes = (pages = {}, expanded = new Set()) => {
  const rows = [];
  const visit = (parentKey, depth) => {
    const page = pages[parentKey] || {};
    for (const node of page.items || []) {
      rows.push({ node, depth });
      if (expanded.has(Number(node.node_index))) visit(String(node.node_index), depth + 1);
    }
    if (page.has_more) rows.push({ kind: 'more', parentKey, depth });
  };
  visit('-1', 0);
  return rows;
};

export const virtualNodeWindow = (rows, scrollTop, viewportHeight, rowHeight = 28, overscan = 6) => {
  const visibleStart = Math.floor(Math.max(0, scrollTop) / rowHeight);
  const visibleCount = Math.ceil(Math.max(rowHeight, viewportHeight) / rowHeight);
  const start = Math.max(0, visibleStart - overscan);
  const end = Math.min(rows.length, visibleStart + visibleCount + overscan);
  return { start, end, topSpacer: start * rowHeight, bottomSpacer: Math.max(0, (rows.length - end) * rowHeight) };
};

