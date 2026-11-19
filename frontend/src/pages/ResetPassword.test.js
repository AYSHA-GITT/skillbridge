import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResetPassword from './ResetPassword';
import authService from '../services/authService';

// react-router-dom 7 does not resolve under CRA's Jest 27, so the router is replaced by a
// minimal stand-in; the page only needs the location, navigate() and <Link>.
let mockLocation = { hash: '', search: '', pathname: '/reset-password' };
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  useLocation: () => mockLocation,
  useNavigate: () => mockNavigate,
  Link: ({ to, children, ...rest }) => <a href={to} {...rest}>{children}</a>,
}), { virtual: true });

jest.mock('../services/authService', () => ({
  __esModule: true,
  default: { verifyResetToken: jest.fn(), resetPassword: jest.fn() },
}));

const TOKEN = 'k6BlELmIGLOk9jUQEzJDX3BJyZYxGP4NxDoQqhTg138';
const INVALID = 'This password reset link is invalid, has expired or has already been used. Request a new link to continue.';

function openWith(hash) {
  mockLocation = { hash, search: '', pathname: '/reset-password' };
  return render(<ResetPassword />);
}

beforeEach(() => {
  jest.clearAllMocks();
  window.history.replaceState(null, '', '/reset-password');
});

test('opening the page directly never shows the password form', async () => {
  openWith('');
  expect(await screen.findByText(/open the link from your password reset email/i)).toBeInTheDocument();
  expect(screen.queryByPlaceholderText(/minimum 8 characters/i)).toBeNull();
  expect(screen.getByText(/request a new reset link/i).closest('a')).toHaveAttribute('href', '/forgot-password');
  expect(authService.verifyResetToken).not.toHaveBeenCalled();
});

test('a tampered token is rejected without calling the server', async () => {
  openWith('#token=abc%27%20OR%201%3D1');
  expect(await screen.findByText(/incomplete or has been changed/i)).toBeInTheDocument();
  expect(authService.verifyResetToken).not.toHaveBeenCalled();
});

test('an expired or used link shows a clear message and a way to get a new one', async () => {
  authService.verifyResetToken.mockRejectedValue({ response: { status: 400, data: { valid: false, error: INVALID } } });
  openWith(`#token=${TOKEN}`);
  expect(await screen.findByText(INVALID)).toBeInTheDocument();
  expect(screen.queryByPlaceholderText(/minimum 8 characters/i)).toBeNull();
  expect(screen.getByText(/request a new reset link/i)).toBeInTheDocument();
});

test('a valid link shows the form, hides the token and resets the password', async () => {
  window.history.replaceState(null, '', `/reset-password#token=${TOKEN}`);
  authService.verifyResetToken.mockResolvedValue({ valid: true, email: 's******@example.com' });
  authService.resetPassword.mockResolvedValue({ message: 'ok' });
  const { container } = openWith(`#token=${TOKEN}`);

  const password = await screen.findByPlaceholderText(/minimum 8 characters/i);
  expect(authService.verifyResetToken).toHaveBeenCalledWith(TOKEN);
  expect(window.location.hash).toBe('');                 // token removed from the address bar
  expect(container.innerHTML).not.toContain(TOKEN);      // and never rendered
  expect(screen.getByText('s******@example.com')).toBeInTheDocument();

  fireEvent.change(password, { target: { value: 'N3w-Strong-Passw0rd' } });
  fireEvent.change(screen.getByPlaceholderText(/repeat new password/i), { target: { value: 'N3w-Strong-Passw0rd' } });
  fireEvent.click(screen.getByRole('button', { name: /save new password/i }));

  await waitFor(() => expect(authService.resetPassword)
    .toHaveBeenCalledWith(TOKEN, 'N3w-Strong-Passw0rd', 'N3w-Strong-Passw0rd'));
  expect(await screen.findByText(/password reset successful/i)).toBeInTheDocument();
});

test('a link that expires while the page is open switches to the new-link screen', async () => {
  authService.verifyResetToken.mockResolvedValue({ valid: true, email: '' });
  authService.resetPassword.mockRejectedValue({
    response: { status: 400, data: { error: INVALID, code: 'invalid_token' } } });
  openWith(`#token=${TOKEN}`);

  fireEvent.change(await screen.findByPlaceholderText(/minimum 8 characters/i), { target: { value: 'N3w-Strong-Passw0rd' } });
  fireEvent.change(screen.getByPlaceholderText(/repeat new password/i), { target: { value: 'N3w-Strong-Passw0rd' } });
  fireEvent.click(screen.getByRole('button', { name: /save new password/i }));

  expect(await screen.findByText(INVALID)).toBeInTheDocument();
  expect(screen.getByText(/request a new reset link/i)).toBeInTheDocument();
});

test('mismatched passwords are caught before any request', async () => {
  authService.verifyResetToken.mockResolvedValue({ valid: true, email: '' });
  openWith(`#token=${TOKEN}`);
  fireEvent.change(await screen.findByPlaceholderText(/minimum 8 characters/i), { target: { value: 'N3w-Strong-Passw0rd' } });
  fireEvent.change(screen.getByPlaceholderText(/repeat new password/i), { target: { value: 'different-123' } });
  fireEvent.click(screen.getByRole('button', { name: /save new password/i }));
  expect(await screen.findByText(/do not match/i)).toBeInTheDocument();
  expect(authService.resetPassword).not.toHaveBeenCalled();
});
