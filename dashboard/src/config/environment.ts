/**
 * Environment configuration module.
 *
 * Reads and validates environment variables from Vite.
 * All environment variables should be prefixed with VITE_ to be exposed to the client.
 */

export interface EnvironmentConfig {
  /** API base URL for backend requests */
  apiBaseUrl: string;

  /** Application environment: development, staging, production */
  appEnv: 'development' | 'staging' | 'production';

  /** Whether to enable React Query DevTools */
  enableDevTools: boolean;

  /** Whether to use mock API instead of real backend */
  enableMockApi: boolean;

  /** Log level for client-side logging */
  logLevel: 'debug' | 'info' | 'warn' | 'error';

  /** Whether to enable performance monitoring */
  enablePerformanceMonitoring: boolean;
}

/**
 * Read and validate environment configuration.
 *
 * @returns Validated environment configuration
 * @throws Error if required variables are missing or invalid
 */
export function getEnvironmentConfig(): EnvironmentConfig {
  const mode = import.meta.env.MODE || 'development';
  const isProduction = mode === 'production';

  return {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',

    appEnv: validateAppEnv(import.meta.env.VITE_APP_ENV || mode),

    enableDevTools: parseBoolean(
      import.meta.env.VITE_ENABLE_DEVTOOLS || (!isProduction).toString()
    ),

    enableMockApi: parseBoolean(import.meta.env.VITE_ENABLE_MOCK_API || 'false'),

    logLevel: validateLogLevel(
      import.meta.env.VITE_LOG_LEVEL || (isProduction ? 'error' : 'debug')
    ),

    enablePerformanceMonitoring: parseBoolean(
      import.meta.env.VITE_ENABLE_PERFORMANCE_MONITORING || 'false'
    ),
  };
}

/**
 * Validate and parse app environment.
 */
function validateAppEnv(env: string): EnvironmentConfig['appEnv'] {
  const validEnvs: EnvironmentConfig['appEnv'][] = [
    'development',
    'staging',
    'production',
  ];

  if (!validEnvs.includes(env as EnvironmentConfig['appEnv'])) {
    console.warn(`Invalid VITE_APP_ENV: ${env}. Defaulting to 'development'.`);
    return 'development';
  }

  return env as EnvironmentConfig['appEnv'];
}

/**
 * Validate and parse log level.
 */
function validateLogLevel(level: string): EnvironmentConfig['logLevel'] {
  const validLevels: EnvironmentConfig['logLevel'][] = [
    'debug',
    'info',
    'warn',
    'error',
  ];

  if (!validLevels.includes(level as EnvironmentConfig['logLevel'])) {
    console.warn(`Invalid VITE_LOG_LEVEL: ${level}. Defaulting to 'debug'.`);
    return 'debug';
  }

  return level as EnvironmentConfig['logLevel'];
}

/**
 * Parse boolean from string.
 */
function parseBoolean(value: string): boolean {
  return value.toLowerCase() === 'true';
}

/**
 * Check if the app is running in development mode.
 */
export function isDevelopment(): boolean {
  return import.meta.env.DEV || import.meta.env.MODE === 'development';
}

/**
 * Check if the app is running in production mode.
 */
export function isProduction(): boolean {
  return import.meta.env.PROD || import.meta.env.MODE === 'production';
}

// Export a singleton config instance
export const config = getEnvironmentConfig();
