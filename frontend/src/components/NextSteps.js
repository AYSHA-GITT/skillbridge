import React from 'react';
import { Link } from 'react-router-dom';
import { TbArrowRight, TbCompass } from 'react-icons/tb';

/**
 * A short list of concrete next actions that link to the page where the student
 * can do them. steps: [{ to, label, detail?, icon? }] - falsy entries are skipped.
 */
export default function NextSteps({ title = 'Next steps', steps = [], className = '' }) {
  const items = steps.filter(Boolean);
  if (items.length === 0) return null;
  return (
    <section className={`glass p-5 rounded-2xl space-y-3 ${className}`} aria-label={title}>
      <h2 className="font-heading text-sm font-bold text-white flex items-center gap-2">
        <TbCompass className="w-4 h-4 text-accent-400" /> {title}
      </h2>
      <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {items.map((s) => {
          const Icon = s.icon || TbArrowRight;
          return (
            <li key={s.to + s.label}>
              <Link to={s.to} className="surface p-3 rounded-xl flex items-start gap-3 hover:border-accent-400/50 transition-colors h-full">
                <Icon className="w-4 h-4 text-accent-300 flex-shrink-0 mt-0.5" />
                <span className="min-w-0">
                  <span className="block text-xs font-semibold text-white">{s.label}</span>
                  {s.detail && <span className="block text-[11px] text-white/50 mt-0.5">{s.detail}</span>}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
