/**
 * 统一错误处理 Composable
 * 用于替代分散的 console.error 调用
 */

/**
 * 错误级别
 */
export const ErrorLevel = {
  DEBUG: 'debug',
  INFO: 'info',
  WARN: 'warn',
  ERROR: 'error',
};

/**
 * 错误处理配置
 */
const config = {
  isDev: import.meta.env.DEV,
  enableConsole: true,
  // 未来可扩展: 上报服务、Toast 通知等
};

/**
 * 格式化错误消息
 * @param {string} context - 上下文标识
 * @param {string} message - 错误消息
 * @param {Error|any} error - 错误对象
 * @returns {string}
 */
function formatMessage(context, message, error) {
  const timestamp = new Date().toISOString().slice(11, 23);
  const errorDetail = error instanceof Error ? error.message : error ? String(error) : '';
  return `[${timestamp}][${context}] ${message}${errorDetail ? ': ' + errorDetail : ''}`;
}

/**
 * 统一错误处理器
 * @param {string} context - 组件/模块名称，用于日志标识
 * @returns {object} 错误处理方法集合
 */
export function useErrorHandler(context = 'App') {
  /**
   * 记录调试信息
   */
  const debug = (message, data = null) => {
    if (config.isDev && config.enableConsole) {
      console.debug(formatMessage(context, message, null), data ?? '');
    }
  };

  /**
   * 记录信息
   */
  const info = (message, data = null) => {
    if (config.enableConsole) {
      console.info(formatMessage(context, message, null), data ?? '');
    }
  };

  /**
   * 记录警告
   */
  const warn = (message, error = null) => {
    if (config.enableConsole) {
      console.warn(formatMessage(context, message, error));
    }
  };

  /**
   * 记录错误
   */
  const error = (message, err = null) => {
    if (config.enableConsole) {
      console.error(formatMessage(context, message, err));
    }
    // 未来扩展: 错误上报
  };

  /**
   * 包装异步函数，自动捕获错误
   * @param {Function} fn - 异步函数
   * @param {string} actionName - 操作名称
   * @returns {Function} 包装后的函数
   */
  const wrapAsync = (fn, actionName = 'operation') => {
    return async (...args) => {
      try {
        return await fn(...args);
      } catch (err) {
        error(`${actionName} failed`, err);
        throw err; // 重新抛出，让调用者决定如何处理
      }
    };
  };

  /**
   * 安全执行异步操作（不抛出错误）
   * @param {Function} fn - 异步函数
   * @param {string} actionName - 操作名称
   * @param {any} fallback - 失败时返回的默认值
   * @returns {Promise<any>}
   */
  const safeAsync = async (fn, actionName = 'operation', fallback = null) => {
    try {
      return await fn();
    } catch (err) {
      error(`${actionName} failed`, err);
      return fallback;
    }
  };

  return {
    debug,
    info,
    warn,
    error,
    wrapAsync,
    safeAsync,
  };
}

/**
 * 全局错误处理器实例（用于非组件代码）
 */
export const globalErrorHandler = useErrorHandler('Global');

export default useErrorHandler;
