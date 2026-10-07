import React, { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import authService from '../services/authService';

/**
 * Route guard that requires an active authenticated session.
 */
export function ProtectedRoute({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    authService.getCurrentUser()
      .then((data) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-base-950 flex items-center justify-center text-white/40 font-mono text-xs">
        <div className="inline-block w-6 h-6 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mr-3" />
        Verifying session...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

/**
 * Route guard that strictly requires Institutional Administrator privileges (role == 'admin').
 * Students attempting to access an AdminRoute are blocked and redirected to /dashboard.
 */
export function AdminRoute({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    authService.getCurrentUser()
      .then((data) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center text-cyan-400 font-mono text-xs">
        <div className="inline-block w-6 h-6 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin mr-3" />
        Verifying Institutional Administrator credentials...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login?portal=admin" state={{ from: location }} replace />;
  }

  const role = (user.role || 'student').toLowerCase();
  if (role !== 'admin') {
    // Student attempting to access admin route -> DENIED, redirect to dashboard
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
