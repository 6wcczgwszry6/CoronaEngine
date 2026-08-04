const pixelValue = (value) => `${Math.max(Number(value) || 0, 0)}px`;

export function createDockOverlayStyles({
  leftVisible = false,
  rightVisible = false,
  leftWidth = 0,
  rightWidth = 0,
  bottomHeight = 0,
  separatorSize = 4,
} = {}) {
  const leftOffset = leftVisible
    ? Math.max(Number(leftWidth) || 0, 0) + Math.max(Number(separatorSize) || 0, 0)
    : 0;
  const rightOffset = rightVisible
    ? Math.max(Number(rightWidth) || 0, 0) + Math.max(Number(separatorSize) || 0, 0)
    : 0;

  return {
    viewport: { inset: '0' },
    left: {
      left: '0',
      top: '0',
      bottom: '0',
      width: pixelValue(leftWidth),
    },
    leftSeparator: {
      left: pixelValue(leftWidth),
      top: '0',
      bottom: '0',
    },
    right: {
      right: '0',
      top: '0',
      bottom: '0',
      width: pixelValue(rightWidth),
    },
    rightSeparator: {
      right: pixelValue(rightWidth),
      top: '0',
      bottom: '0',
    },
    bottom: {
      left: pixelValue(leftOffset),
      right: pixelValue(rightOffset),
      bottom: '0',
      height: pixelValue(bottomHeight),
    },
    bottomSeparator: {
      left: pixelValue(leftOffset),
      right: pixelValue(rightOffset),
      bottom: pixelValue(bottomHeight),
    },
  };
}
