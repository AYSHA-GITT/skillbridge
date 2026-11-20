import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';
import authService from './services/authService';

// The real router and route guards are exercised; only the network layer is replaced.
// (react-router-dom 7 resolves under CRA's Jest 27 through the moduleNameMapper in package.json.)
jest.mock('./services/api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(() => Promise.reject(new Error('network disabled in tests'))),
    post: jest.fn(() => Promise.reject(new Error('network disabled in tests'))),
    put: jest.fn(() => Promise.reject(new Error('network disabled in tests'))),
    delete: jest.fn(() => Promise.reject(new Error('network disabled in tests')))
  }
}));
jest.mock('./services/authService', () => ({
  __esModule: true,
  default: { getCurrentUser: jest.fn(), logout: jest.fn(), login: jest.fn(), register: jest.fn() }
}));

function openAt(path) {
  window.history.pushState({}, '', path);
  return render(<App />);
}

beforeEach(() => {
  jest.clearAllMocks();
  authService.getCurrentUser.mockRejectedValue(new Error('not logged in'));
});

test('the landing page is served at /', () => {
  openAt('/');
  expect(screen.getByText(/Close Your Skill Gap/i)).toBeInTheDocument();
});

test('unknown paths redirect to the landing page', async () => {
  openAt('/this/page/does/not/exist');
  expect(await screen.findByText(/Close Your Skill Gap/i)).toBeInTheDocument();
  expect(window.location.pathname).toBe('/');
});

test('student pages send signed-out visitors to the student sign-in', async () => {
  openAt('/roadmap');
  expect(await screen.findByText('Student Sign In')).toBeInTheDocument();
  expect(window.location.pathname).toBe('/login');
});

test('recruiter pages send signed-out visitors to the recruiter sign-in', async () => {
  openAt('/recruiter/verifications');
  expect(await screen.findByText('Recruiter Sign In')).toBeInTheDocument();
  expect(window.location.search).toBe('?portal=recruiter');
});

test('a student cannot open the recruiter portal', async () => {
  authService.getCurrentUser.mockResolvedValue({ id: 1, name: 'Asha', role: 'student' });
  openAt('/recruiter/verifications');
  // RecruiterRoute sends students to their own dashboard
  await waitFor(() => expect(window.location.pathname).toBe('/dashboard'));
});

test('a recruiter is kept out of student pages', async () => {
  authService.getCurrentUser.mockResolvedValue({ id: 2, name: 'Rita', role: 'recruiter' });
  openAt('/employer-access');
  await waitFor(() => expect(window.location.pathname).toBe('/recruiter'));
});
