/**
 * Password-reset links look like /reset-password#token=<token>. The token is in the URL
 * fragment, which browsers never send to a server or in a Referer header. Older links used
 * ?token=<token>; both are read so a link e-mailed before an update still works.
 */
const TOKEN_PATTERN = /^[A-Za-z0-9_-]{20,128}$/;

export function readResetToken(hash = '', search = '') {
  const fromHash = new URLSearchParams(String(hash).replace(/^#/, '')).get('token');
  const fromQuery = new URLSearchParams(String(search).replace(/^\?/, '')).get('token');
  const token = (fromHash || fromQuery || '').trim();
  return TOKEN_PATTERN.test(token) ? token : '';
}

/** True when the URL carried something that looked like a token but was malformed. */
export function hasMalformedToken(hash = '', search = '') {
  const raw = new URLSearchParams(String(hash).replace(/^#/, '')).get('token')
    || new URLSearchParams(String(search).replace(/^\?/, '')).get('token');
  return Boolean(raw) && !readResetToken(hash, search);
}

/**
 * Removes the token from the address bar and browser history once it has been read, so it
 * is not left in history, bookmarks or screenshots.
 */
export function scrubTokenFromUrl(win = typeof window !== 'undefined' ? window : null) {
  if (!win || !win.history || typeof win.history.replaceState !== 'function') return;
  const { pathname } = win.location;
  win.history.replaceState(win.history.state, '', pathname);
}
