import { readResetToken, hasMalformedToken, scrubTokenFromUrl } from './resetToken';

const TOKEN = 'k6BlELmIGLOk9jUQEzJDX3BJyZYxGP4NxDoQqhTg138';

describe('readResetToken', () => {
  test('reads the token from the URL fragment', () => {
    expect(readResetToken(`#token=${TOKEN}`, '')).toBe(TOKEN);
  });

  test('still reads links in the older ?token= form', () => {
    expect(readResetToken('', `?token=${TOKEN}`)).toBe(TOKEN);
  });

  test('missing token gives an empty string', () => {
    expect(readResetToken('', '')).toBe('');
    expect(readResetToken('#', '?')).toBe('');
    expect(hasMalformedToken('', '')).toBe(false);
  });

  test('tampered or malformed tokens are rejected before any request', () => {
    for (const bad of ['short', `${TOKEN}<script>`, "' OR '1'='1", '../../etc', 'x'.repeat(200)]) {
      expect(readResetToken(`#token=${encodeURIComponent(bad)}`, '')).toBe('');
      expect(hasMalformedToken(`#token=${encodeURIComponent(bad)}`, '')).toBe(true);
    }
  });
});

describe('scrubTokenFromUrl', () => {
  test('replaces the address with the bare path', () => {
    const replaceState = jest.fn();
    scrubTokenFromUrl({ location: { pathname: '/reset-password' }, history: { state: null, replaceState } });
    expect(replaceState).toHaveBeenCalledWith(null, '', '/reset-password');
  });

  test('does nothing without a history API', () => {
    expect(() => scrubTokenFromUrl({ location: { pathname: '/' } })).not.toThrow();
    expect(() => scrubTokenFromUrl(null)).not.toThrow();
  });
});
