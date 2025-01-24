type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  data?: any;
}

class Logger {
  private static instance: Logger;
  private logs: LogEntry[] = [];
  private readonly maxLogs = 1000;
  private logLevel: LogLevel = 'info';

  private constructor() {
    // Initialize logger
    this.setLogLevel(process.env.NODE_ENV === 'development' ? 'debug' : 'info');
  }

  static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  setLogLevel(level: LogLevel) {
    this.logLevel = level;
    this.info(`Log level set to: ${level}`);
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error'];
    return levels.indexOf(level) >= levels.indexOf(this.logLevel);
  }

  private formatMessage(level: LogLevel, message: string, data?: any): LogEntry {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
    };

    if (data) {
      entry.data = this.sanitizeData(data);
    }

    return entry;
  }

  private sanitizeData(data: any): any {
    if (!data) return data;

    // Deep clone the data
    const clonedData = JSON.parse(JSON.stringify(data));

    // Remove sensitive information
    const sensitiveFields = ['password', 'token', 'authorization', 'secret'];
    const sanitize = (obj: any) => {
      if (typeof obj !== 'object' || obj === null) return;

      Object.keys(obj).forEach(key => {
        if (sensitiveFields.includes(key.toLowerCase())) {
          obj[key] = '[REDACTED]';
        } else if (typeof obj[key] === 'object') {
          sanitize(obj[key]);
        }
      });
    };

    sanitize(clonedData);
    return clonedData;
  }

  private addLog(entry: LogEntry) {
    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }

    // Console output for development
    const consoleMsg = `[${entry.level.toUpperCase()}] ${entry.message}`;
    switch (entry.level) {
      case 'debug':
        console.debug(consoleMsg, entry.data || '');
        break;
      case 'info':
        console.info(consoleMsg, entry.data || '');
        break;
      case 'warn':
        console.warn(consoleMsg, entry.data || '');
        break;
      case 'error':
        console.error(consoleMsg, entry.data || '');
        break;
    }
  }

  debug(message: string, data?: any) {
    if (this.shouldLog('debug')) {
      this.addLog(this.formatMessage('debug', message, data));
    }
  }

  info(message: string, data?: any) {
    if (this.shouldLog('info')) {
      this.addLog(this.formatMessage('info', message, data));
    }
  }

  warn(message: string, data?: any) {
    if (this.shouldLog('warn')) {
      this.addLog(this.formatMessage('warn', message, data));
    }
  }

  error(message: string, error?: any) {
    if (this.shouldLog('error')) {
      const errorData = error ? {
        message: error.message,
        stack: error.stack,
        ...error
      } : undefined;
      this.addLog(this.formatMessage('error', message, errorData));
    }
  }

  getLogs(): LogEntry[] {
    return [...this.logs];
  }

  clearLogs() {
    this.logs = [];
    this.info('Logs cleared');
  }

  // Export logs as JSON file
  exportLogs(): string {
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV,
      logs: this.logs
    }, null, 2);
  }
}

export const logger = Logger.getInstance(); 