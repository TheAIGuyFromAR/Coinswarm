/**
 * Structured Logging Framework for Cloudflare Workers
 *
 * Provides structured logging with consistent formatting, log levels,
 * and context enrichment for better observability.
 */

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

export interface LogContext {
  worker?: string;
  agent_id?: string;
  pattern_id?: string;
  cycle?: number;
  pair?: string;
  request_id?: string;
  [key: string]: any;
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: LogContext;
  error?: {
    name: string;
    message: string;
    stack?: string;
  };
}

export class StructuredLogger {
  private workerName: string;
  private minLevel: LogLevel;
  private defaultContext: LogContext;

  constructor(workerName: string, minLevel: LogLevel = LogLevel.INFO, defaultContext: LogContext = {}) {
    this.workerName = workerName;
    this.minLevel = minLevel;
    this.defaultContext = { worker: workerName, ...defaultContext };
  }

  /**
   * Check if a log level should be output based on minimum level
   */
  private shouldLog(level: LogLevel): boolean {
    const levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR];
    const minIndex = levels.indexOf(this.minLevel);
    const currentIndex = levels.indexOf(level);
    return currentIndex >= minIndex;
  }

  /**
   * Create a structured log entry
   */
  private createLogEntry(
    level: LogLevel,
    message: string,
    context?: LogContext,
    error?: Error
  ): LogEntry {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      context: { ...this.defaultContext, ...context },
    };

    if (error) {
      entry.error = {
        name: error.name,
        message: error.message,
        stack: error.stack,
      };
    }

    return entry;
  }

  /**
   * Output a log entry to console
   */
  private output(entry: LogEntry): void {
    const formatted = JSON.stringify(entry);

    switch (entry.level) {
      case LogLevel.ERROR:
        console.error(formatted);
        break;
      case LogLevel.WARN:
        console.warn(formatted);
        break;
      case LogLevel.INFO:
        console.info(formatted);
        break;
      case LogLevel.DEBUG:
      default:
        console.log(formatted);
        break;
    }
  }

  /**
   * Log a debug message
   */
  debug(message: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    const entry = this.createLogEntry(LogLevel.DEBUG, message, context);
    this.output(entry);
  }

  /**
   * Log an info message
   */
  info(message: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.INFO)) return;
    const entry = this.createLogEntry(LogLevel.INFO, message, context);
    this.output(entry);
  }

  /**
   * Log a warning message
   */
  warn(message: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.WARN)) return;
    const entry = this.createLogEntry(LogLevel.WARN, message, context);
    this.output(entry);
  }

  /**
   * Log an error message
   */
  error(message: string, contextOrError?: LogContext | Error, error?: Error): void {
    if (!this.shouldLog(LogLevel.ERROR)) return;

    let context: LogContext | undefined;
    let err: Error | undefined;

    // Handle overloaded parameters
    if (contextOrError instanceof Error) {
      err = contextOrError;
      context = undefined;
    } else {
      context = contextOrError;
      err = error;
    }

    const entry = this.createLogEntry(LogLevel.ERROR, message, context, err);
    this.output(entry);
  }

  /**
   * Create a child logger with additional default context
   */
  child(additionalContext: LogContext): StructuredLogger {
    const childContext = { ...this.defaultContext, ...additionalContext };
    return new StructuredLogger(this.workerName, this.minLevel, childContext);
  }

  /**
   * Update the default context
   */
  updateContext(context: LogContext): void {
    this.defaultContext = { ...this.defaultContext, ...context };
  }
}

/**
 * Create a logger instance for a worker
 */
export function createLogger(
  workerName: string,
  minLevel: LogLevel = LogLevel.INFO
): StructuredLogger {
  return new StructuredLogger(workerName, minLevel);
}

/**
 * Legacy console.log compatibility layer for gradual migration
 */
export function createLegacyLogger(workerName: string) {
  const logger = createLogger(workerName);

  return {
    log: (message: string, ...args: any[]) => {
      if (args.length > 0) {
        logger.info(message, { args });
      } else {
        logger.info(message);
      }
    },
    error: (message: string, error?: Error) => {
      if (error instanceof Error) {
        logger.error(message, error);
      } else {
        logger.error(message);
      }
    },
    warn: (message: string, context?: any) => {
      logger.warn(message, context);
    },
    info: (message: string, context?: any) => {
      logger.info(message, context);
    },
  };
}
