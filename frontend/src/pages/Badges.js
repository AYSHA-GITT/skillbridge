import React, { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import BadgeCard from '../components/BadgeCard';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import { TbTrophy } from 'react-icons/tb';

export default function Badges() {
  const [badges, setBadges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, unlocked, locked
  const [error, setError] = useState('');

  useEffect(() => {
    skillService.getBadges()
      .then((res) => {
        setBadges(res.badges || []);
      })
      .catch(() => {
        setError('Failed to load badges.');
      })
      .finally(() => setLoading(false));
  }, []);

  const unlockedCount = badges.filter((b) => b.unlocked).length;

  const filteredBadges = badges.filter((b) => {
    if (filter === 'unlocked') return b.unlocked;
    if (filter === 'locked') return !b.unlocked;
    return true;
  });

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-white">
              Badges & Achievements
            </h1>
            <p className="text-white/50 text-sm mt-1">
              Milestones unlocked as you verify skills, pass quizzes, and adhere to privacy best practices.
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-base-900 px-3.5 py-2 rounded-xl border border-base-700/60">
            <TbTrophy className="w-5 h-5 text-accent-400" />
            <span className="text-xs font-mono font-semibold text-white">
              {unlockedCount} / {badges.length} Unlocked
            </span>
          </div>
        </div>

        {error && <AlertBanner type="error" message={error} onClose={() => setError('')} />}

        {/* Filter Pills */}
        <div className="flex space-x-2 bg-base-900 p-1 rounded-xl border border-base-700/60 w-fit">
          {['all', 'unlocked', 'locked'].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                filter === tab
                  ? 'bg-accent-500/20 text-accent-300 border border-accent-400/30 font-semibold'
                  : 'text-white/50 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Badges Grid */}
        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Evaluating milestone credentials...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredBadges.map((badge) => (
              <BadgeCard key={badge.id} badge={badge} />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
