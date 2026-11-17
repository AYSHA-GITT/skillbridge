import { apiErrorMessage, websiteError } from './apiErrors';

describe('apiErrorMessage', () => {
  test('backend unreachable is reported, not hidden behind the fallback', () => {
    const networkError = { message: 'Network Error', code: 'ERR_NETWORK' }; // axios: no response
    const msg = apiErrorMessage(networkError, 'Registration failed');
    expect(msg).toMatch(/cannot reach the skillbridge server/i);
    expect(msg).not.toBe('Registration failed');
  });

  test('timeout', () => {
    expect(apiErrorMessage({ code: 'ECONNABORTED', message: 'timeout of 0ms exceeded' }))
      .toMatch(/took too long/i);
  });

  test('server message wins (duplicate email, invalid website)', () => {
    const dup = { response: { status: 409, data: { error: 'An account with this email already exists' } } };
    expect(apiErrorMessage(dup, 'Registration failed')).toBe('An account with this email already exists');
    const site = { response: { status: 400, data: { error: 'Website must be a full http(s) link (e.g. https://example.com)' } } };
    expect(apiErrorMessage(site, 'Registration failed')).toMatch(/website must be a full http/i);
  });

  test('rate limit gives a wait time', () => {
    const err = { response: { status: 429, data: { retry_after_seconds: 1800 }, headers: {} } };
    expect(apiErrorMessage(err)).toBe('Too many attempts. Please wait about 30 minutes and try again.');
  });

  test('server crash with an HTML body is described as a server error', () => {
    const err = { response: { status: 500, data: '<!doctype html><title>500</title>' } };
    expect(apiErrorMessage(err, 'Registration failed')).toMatch(/unexpected error \(HTTP 500\)/);
  });

  test('other responses without a message fall back', () => {
    expect(apiErrorMessage({ response: { status: 400, data: {} } }, 'Registration failed')).toBe('Registration failed');
  });
});

describe('websiteError (mirrors the server rule)', () => {
  test('optional: blank is fine', () => {
    expect(websiteError('')).toBeNull();
    expect(websiteError('   ')).toBeNull();
  });

  test('full http(s) links are accepted', () => {
    expect(websiteError('https://acme.example.com')).toBeNull();
    expect(websiteError('http://acme.in/careers')).toBeNull();
    expect(websiteError('  https://acme.com  ')).toBeNull();
  });

  test('links the server would reject are caught before submitting', () => {
    for (const bad of ['acme.com', 'www.acme.com', 'ftp://acme.com', 'javascript:alert(1)', 'https://acme .com',
      'https://' + 'a'.repeat(500)]) {
      expect(websiteError(bad)).toMatch(/valid website/i);
    }
  });
});
