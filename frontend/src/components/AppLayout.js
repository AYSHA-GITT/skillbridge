import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import AskAssistantModal from './AskAssistantModal';
import PrivacyInfoModal from './PrivacyInfoModal';
import authService from '../services/authService';

export default function AppLayout({ children, fullWidth = false }) {
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [privacyModalOpen, setPrivacyModalOpen] = useState(false);

  const refreshUser = () => {
    authService.getCurrentUser()
      .then((data) => setStudent(data))
      .catch(() => {});
  };

  useEffect(() => {
    authService.getCurrentUser()
      .then((data) => setStudent(data))
      .catch(() => navigate('/login'))
      .finally(() => setLoading(false));

    const handleProfileUpdated = (e) => {
      if (e?.detail) {
        setStudent(e.detail);
      } else {
        refreshUser();
      }
    };

    window.addEventListener('skillbridge:profileUpdated', handleProfileUpdated);
    return () => {
      window.removeEventListener('skillbridge:profileUpdated', handleProfileUpdated);
    };
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
    <div className="min-h-screen flex flex-col bg-base-950 relative">
      <Navbar
        student={student}
        onOpenAssistant={() => setAssistantOpen(true)}
        onOpenPrivacyModal={() => setPrivacyModalOpen(true)}
      />
      <div className={`flex-1 flex w-full mx-auto ${fullWidth ? 'max-w-[1600px] px-2 md:px-4' : 'max-w-7xl'}`}>
        <Sidebar onOpenPrivacyModal={() => setPrivacyModalOpen(true)} />
        <main className={`flex-1 p-4 md:p-8 overflow-y-auto ${fullWidth ? 'w-full' : 'max-w-5xl'}`}>
          {children}
        </main>
      </div>

      {/* Floating Grounded AI Assistant docked at bottom-right */}
      <AskAssistantModal
        isOpen={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        onOpen={() => setAssistantOpen(true)}
      />

      {/* Informational Privacy Guarantees Modal */}
      <PrivacyInfoModal
        isOpen={privacyModalOpen}
        onClose={() => setPrivacyModalOpen(false)}
      />
    </div>
  );
}
