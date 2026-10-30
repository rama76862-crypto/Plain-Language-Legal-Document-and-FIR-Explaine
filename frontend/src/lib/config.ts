/**
 * NyayaSarathi App Configuration
 */

export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  apiProxyTarget: import.meta.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
  useFixtures: import.meta.env.VITE_USE_FIXTURES === 'true',
  inactivityTimeoutMinutes: Number(import.meta.env.VITE_INACTIVITY_TIMEOUT_MINUTES) || 30,
};
