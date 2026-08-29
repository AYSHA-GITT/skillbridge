import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import authService from '../services/authService';

export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authService.getCurrentUser()
      .then((data) => setStudent(data))
      .catch(() => navigate('/login'))
      .finally(() => setLoading(false));
  }, [navigate]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-white/40 font-mono text-sm">
        <div className="inline-block w-6 h-6 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mr-3" />
        Authenticating SkillBridge session...
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-base-950">
      <Navbar student={student} />
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <Sidebar />
        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-5xl">
          {children}
        </main>
      </div>
    </div>
  );
}
