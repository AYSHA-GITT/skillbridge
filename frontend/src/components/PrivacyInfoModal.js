import React from 'react';
import { TbShieldCheck, TbX, TbCheck } from 'react-icons/tb';

export default function PrivacyInfoModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-base-950/80 backdrop-blur-sm animate-fade-in">
      <div className="glass max-w-lg w-full p-6 sm:p-7 rounded-3xl border border-teal-500/30 relative shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-white/50 hover:text-white hover:bg-white/5 transition-colors"
          title="Close"
        >
          <TbX className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-10 rounded-2xl bg-teal-500/20 text-teal-300 border border-teal-400/30 flex items-center justify-center">
            <TbShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-heading text-lg font-bold text-white">
              Privacy-Preserving Intelligence
            </h2>
            <p className="text-xs text-white/50">
              How SkillBridge guarantees your personal career data sovereignty
            </p>
          </div>
        </div>

        <p className="text-xs text-white/80 leading-relaxed mb-4">
          Your career and academic data is protected using state-of-the-art privacy-preserving machine learning techniques. We believe educational intelligence should never require sacrificing personal privacy.
        </p>

        <div className="space-y-2.5 mb-5">
          <div className="surface p-3 rounded-xl border border-base-700/60 flex items-start space-x-3">
            <div className="p-1 rounded-lg bg-emerald-500/20 text-emerald-400 mt-0.5">
              <TbCheck className="w-3.5 h-3.5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-white">Raw training data remains local</p>
              <p className="text-[11px] text-white/50 mt-0.5">
                Your uploaded resume text, academic transcripts, and individual quiz answers are never sent to external servers or central repositories.
              </p>
            </div>
          </div>

          <div className="surface p-3 rounded-xl border border-base-700/60 flex items-start space-x-3">
            <div className="p-1 rounded-lg bg-emerald-500/20 text-emerald-400 mt-0.5">
              <TbCheck className="w-3.5 h-3.5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-white">Model updates are shared</p>
              <p className="text-[11px] text-white/50 mt-0.5">
                Only numerical weight adjustments (gradients) generated through local training are communicated with the research network.
              </p>
            </div>
          </div>

          <div className="surface p-3 rounded-xl border border-base-700/60 flex items-start space-x-3">
            <div className="p-1 rounded-lg bg-emerald-500/20 text-emerald-400 mt-0.5">
              <TbCheck className="w-3.5 h-3.5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-white">Federated aggregation is used</p>
              <p className="text-[11px] text-white/50 mt-0.5">
                Institutional nodes collaboratively synchronize models using Federated Averaging (FedAvg), synthesizing collective career insights.
              </p>
            </div>
          </div>

          <div className="surface p-3 rounded-xl border border-base-700/60 flex items-start space-x-3">
            <div className="p-1 rounded-lg bg-emerald-500/20 text-emerald-400 mt-0.5">
              <TbCheck className="w-3.5 h-3.5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-white">Differential Privacy provides additional protection</p>
              <p className="text-[11px] text-white/50 mt-0.5">
                Calibrated Gaussian noise and gradient clipping provide mathematical guarantees against membership inference or data reconstruction.
              </p>
            </div>
          </div>
        </div>

        <div className="p-3 bg-teal-950/30 border border-teal-500/20 rounded-xl text-[11px] text-teal-200/80 mb-5">
          Federated Learning reduces the need to transfer raw training data. Differential Privacy provides an additional mathematical privacy protection layer.
        </div>

        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="btn-primary text-xs py-2 px-5"
          >
            Got It
          </button>
        </div>
      </div>
    </div>
  );
}
