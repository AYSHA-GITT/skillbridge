import React from 'react';
import { TbAlertCircle, TbCircleCheck, TbInfoCircle, TbX } from 'react-icons/tb';

export default function AlertBanner({ type = 'info', message, onClose }) {
  if (!message) return null;

  const styles = {
    error: 'bg-red-500/10 border-red-500/30 text-red-300',
    success: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
    info: 'bg-accent-500/10 border-accent-400/30 text-accent-300',
    warning: 'bg-amber-500/10 border-amber-500/30 text-amber-300'
  };

  const icons = {
    error: <TbAlertCircle className="w-5 h-5 flex-shrink-0 text-red-400" />,
    success: <TbCircleCheck className="w-5 h-5 flex-shrink-0 text-emerald-400" />,
    info: <TbInfoCircle className="w-5 h-5 flex-shrink-0 text-accent-400" />,
    warning: <TbAlertCircle className="w-5 h-5 flex-shrink-0 text-amber-400" />
  };

  return (
    <div className={`flex items-center justify-between p-4 rounded-xl border mb-4 backdrop-blur-sm ${styles[type] || styles.info}`}>
      <div className="flex items-center space-x-3">
        {icons[type] || icons.info}
        <span className="text-sm font-medium">{message}</span>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-white/40 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/5"
          aria-label="Close"
        >
          <TbX className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
