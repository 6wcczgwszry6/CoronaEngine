/**
 * 事件总线 —— 同一 JS 上下文内的发布-订阅
 * Python 通过 execute_javascript 调用 window.__coronaEmit(event, ...args)
 * 所有订阅该事件的 Vue 组件都会收到通知
 */
export const coronaEventBus = {
  _handlers: {},

  on(event, handler) {
    if (!this._handlers[event]) {
      this._handlers[event] = [];
    }
    this._handlers[event].push(handler);
  },

  off(event, handler) {
    if (!this._handlers[event]) return;
    if (!handler) {
      delete this._handlers[event];
    } else {
      this._handlers[event] = this._handlers[event].filter((h) => h !== handler);
    }
  },

  emit(event, ...args) {
    if (!this._handlers[event]) return;
    for (const h of this._handlers[event]) {
      try {
        h(...args);
      } catch (e) {
        console.error(`[coronaEventBus] handler error for "${event}":`, e);
      }
    }
  },
};

/**
 * C++ __cross_tab__ 广播 + Python js_call_func 推送的统一入口
 * 被 C++ 的 ExecuteJavaScript 或 Python 的 execute_javascript 调用
 */
window.__coronaEmit = (event, ...args) => {
  coronaEventBus.emit(event, ...args);
};
