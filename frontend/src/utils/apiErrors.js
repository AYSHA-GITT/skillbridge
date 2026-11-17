/**
 * Turns an axios error into a message a person can act on.
 *
 * The server's own message (`{ error: ... }`) always wins: it already says things like
 * "An account with this email already exists" or "Website must be a full http(s) link".
 * Without one, the failure is described by what actually happened instead of a generic
 * "Registration failed": the server could not be reached, refused for too many attempts,
 * or hit an internal error.
 */
export function apiErrorMessage(err, fallback = 'Something went wrong. Please try again.') {
  const res = err && err.response;
  if (!res) {
    // No HTTP response at all: backend not running, network down, or the request was blocked
    if (err && (err.code === 'ECONNABORTED' || /timeout/i.test(err.message || ''))) {
      return 'The server took too long to respond. Please try again.';
    }
    return 'Cannot reach the SkillBridge server. Check that the backend is running and your connection is working, then try again.';
  }
  const data = res.data;
  if (data && typeof data === 'object' && typeof data.error === 'string' && data.error.trim()) {
    return data.error;
  }
  if (res.status === 429) {
    const wait = Number((data && data.retry_after_seconds) || res.headers?.['retry-after']);
    const minutes = wait > 0 ? Math.ceil(wait / 60) : null;
    return minutes
      ? `Too many attempts. Please wait about ${minutes} minute${minutes === 1 ? '' : 's'} and try again.`
      : 'Too many attempts. Please wait a few minutes and try again.';
  }
  if (res.status >= 500) {
    return `The server hit an unexpected error (HTTP ${res.status}). Please try again in a moment.`;
  }
  return fallback;
}

/**
 * Website is optional; when given it must be a full http(s) link. Mirrors the server rule
 * (backend utils/skill_passport.is_safe_url: ^https?://[^\s<>"']+$, at most 500 characters)
 * so the form never rejects what the server accepts, or the reverse.
 */
export function websiteError(value) {
  const v = (value || '').trim();
  if (!v) return null;
  if (!/^https?:\/\/[^\s<>"']+$/i.test(v) || v.length > 500) {
    return 'Please enter a valid website starting with https:// (for example https://example.com), or leave it blank.';
  }
  return null;
}
