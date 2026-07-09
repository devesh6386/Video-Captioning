/**
 * API Client - Environment-aware HTTP client for backend communication
 * 
 * Environment Variables:
 * - VITE_API_BASE_URL: Backend URL (default: current origin)
 *   Examples:
 *     - Development: http://localhost:8000
 *     - Production: https://video-captioning-api.onrender.com
 */

/**
 * Get the API base URL from environment or infer from location
 */
function getApiBaseUrl() {
  // First check Vite environment variable
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  // In production (Vercel), use current origin if no explicit URL set
  // In development with proxy, use relative URLs
  if (import.meta.env.DEV) {
    // Dev mode: proxy will handle routing to http://localhost:8000
    return '';
  }

  // Production: use the current origin (Vercel serves both frontend and proxies to backend)
  // OR if backend is on different domain, VITE_API_BASE_URL must be set
  return '';
}

/**
 * Construct full endpoint URL
 */
export function getEndpoint(path) {
  const baseUrl = getApiBaseUrl();
  return `${baseUrl}${path}`;
}

/**
 * Enhanced fetch with logging, error handling, and proper headers
 */
export async function apiCall(endpoint, options = {}) {
  const url = getEndpoint(endpoint);
  const defaultOptions = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const config = { ...defaultOptions, ...options };

  // Log request
  console.log(`[API] ${config.method} ${url}`, {
    body: options.body ? 'included' : 'none',
    timestamp: new Date().toISOString(),
  });

  try {
    const startTime = performance.now();
    const response = await fetch(url, config);
    const duration = (performance.now() - startTime).toFixed(0);

    console.log(`[API] Response - Status: ${response.status}, Duration: ${duration}ms`, {
      url,
      status: response.status,
      statusText: response.statusText,
    });

    // Always try to parse response body for debugging
    let data;
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errorMessage = 
        (data && data.detail) || 
        (typeof data === 'string' ? data : null) ||
        `Server error: ${response.status} ${response.statusText}`;
      
      console.error(`[API] Error Response:`, {
        status: response.status,
        message: errorMessage,
        data,
      });

      const error = new Error(errorMessage);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    console.log(`[API] Success - ${endpoint}`, { data });
    return data;
  } catch (error) {
    // Network errors
    if (error instanceof TypeError) {
      const networkError = `Network Error: ${error.message}. Check if backend is running at ${url}`;
      console.error(`[API] Network Error:`, {
        message: networkError,
        originalError: error.message,
        url,
      });
      throw new Error(networkError);
    }

    // Re-throw with enhanced info
    console.error(`[API] Request Failed:`, {
      endpoint,
      url,
      message: error.message,
      status: error.status,
    });
    throw error;
  }
}

/**
 * Validate API response has expected structure
 */
export function validateCaptionResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Invalid response: expected JSON object');
  }

  if (!data.captions || typeof data.captions !== 'object') {
    throw new Error('Invalid response: missing captions object');
  }

  const requiredStyles = ['formal', 'sarcastic', 'humorous_tech', 'humorous_non_tech'];
  const missingStyles = requiredStyles.filter(s => !data.captions[s]);
  
  if (missingStyles.length > 0) {
    throw new Error(`Missing caption styles: ${missingStyles.join(', ')}`);
  }

  return data;
}

/**
 * Health check to verify backend connectivity
 */
export async function checkBackendHealth() {
  try {
    const data = await apiCall('/api/health');
    console.log('[API] Backend health check passed:', data);
    return { 
      ok: true, 
      data,
      baseUrl: getApiBaseUrl() || 'same-origin',
    };
  } catch (error) {
    console.error('[API] Backend health check failed:', error.message);
    return {
      ok: false,
      error: error.message,
      baseUrl: getApiBaseUrl() || 'same-origin',
    };
  }
}
