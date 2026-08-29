import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  TbShieldCheck,
  TbBrain,
  TbCoin,
  TbSparkles,
  TbLockCheck,
  TbArrowRight
} from 'react-icons/tb';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-base-950 text-white selection:bg-accent-400 selection:text-base-950">
      {/* Navigation */}
      <nav className="w-full border-b border-base-700/60 bg-base-950/70 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-400 to-teal-600 flex items-center justify-center text-base-950 font-bold shadow-glow">
              <TbSparkles className="w-5 h-5" />
            </div>
            <span className="font-heading font-bold text-xl tracking-tight text-white">
              SkillBridge
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              to="/login"
              className="text-sm font-medium text-white/70 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="btn-primary text-xs py-2 px-4 shadow-glow"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-20 pb-28 px-6 max-w-5xl mx-auto text-center overflow-hidden">
        <div className="glow-teal absolute top-10 left-1/2 -translate-x-1/2 w-96 h-96 opacity-30" />

        <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-accent-500/10 border border-accent-400/30 text-accent-300 text-xs font-mono mb-8">
          <TbLockCheck className="w-4 h-4 text-accent-400" />
          <span>Next-Gen Privacy-Preserving Education Tech</span>
        </div>

        <h1 className="font-heading text-4xl sm:text-6xl font-bold tracking-tight leading-tight mb-6">
          Close Your Skill Gap <br />
          <span className="bg-gradient-to-r from-accent-300 via-teal-400 to-emerald-400 bg-clip-text text-transparent">
            Without Compromising Your Privacy
          </span>
        </h1>

        <p className="text-white/60 text-lg sm:text-xl max-w-3xl mx-auto mb-10 leading-relaxed">
          SkillBridge analyzes your resume, evaluates skills with adaptive quizzes,
          and generates personalized roadmaps — trained collaboratively with <span className="text-white font-medium">Federated Learning</span> so your personal resume data never leaves your device.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => navigate('/register')}
            className="btn-primary text-base py-3.5 px-8 max-w-xs flex items-center justify-center space-x-2 font-semibold shadow-glow"
          >
            <span>Start Free Analysis</span>
            <TbArrowRight className="w-5 h-5" />
          </button>
          <button
            onClick={() => navigate('/login')}
            className="btn-ghost text-base py-3.5 px-8 max-w-xs"
          >
            Sign In to Dashboard
          </button>
        </div>
      </section>

      {/* Pillars Section */}
      <section className="py-20 px-6 max-w-6xl mx-auto border-t border-base-800">
        <div className="text-center mb-16">
          <h2 className="font-heading text-2xl sm:text-3xl font-bold mb-3">
            Engineered for Tomorrow's Engineers
          </h2>
          <p className="text-white/50 text-sm max-w-xl mx-auto">
            Combining state-of-the-art decentralized AI, psychometric skill verification, and real market telemetry.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass p-6 rounded-2xl relative overflow-hidden group hover:border-accent-400/40 transition-all">
            <div className="w-12 h-12 rounded-xl bg-accent-500/10 border border-accent-400/20 text-accent-400 flex items-center justify-center mb-5">
              <TbShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="font-heading font-semibold text-lg mb-2">Federated Learning</h3>
            <p className="text-white/50 text-sm leading-relaxed">
              Models are trained on localized institutional partitions. Only secure, differentially private weight updates are aggregated to the central server.
            </p>
          </div>

          <div className="glass p-6 rounded-2xl relative overflow-hidden group hover:border-accent-400/40 transition-all">
            <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-400/20 text-teal-400 flex items-center justify-center mb-5">
              <TbBrain className="w-6 h-6" />
            </div>
            <h3 className="font-heading font-semibold text-lg mb-2">Evidence-Based Quizzes</h3>
            <p className="text-white/50 text-sm leading-relaxed">
              Don't just claim skills. Adaptive AI evaluates your comprehension with tailored multi-tier questions to establish verified competency.
            </p>
          </div>

          <div className="glass p-6 rounded-2xl relative overflow-hidden group hover:border-accent-400/40 transition-all">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-400/20 text-emerald-400 flex items-center justify-center mb-5">
              <TbCoin className="w-6 h-6" />
            </div>
            <h3 className="font-heading font-semibold text-lg mb-2">Salary Simulator</h3>
            <p className="text-white/50 text-sm leading-relaxed">
              See the direct financial ROI of your learning path. Predict potential LPA growth for every missing skill you acquire and verify.
            </p>
          </div>
        </div>
      </section>

      {/* Federated Flow Explanation */}
      <section className="py-20 px-6 max-w-5xl mx-auto border-t border-base-800">
        <div className="glass p-8 md:p-12 rounded-3xl relative overflow-hidden">
          <div className="glow-teal absolute -right-16 -top-16 w-80 h-80 opacity-20" />
          <div className="max-w-2xl">
            <span className="text-xs font-mono uppercase tracking-wider text-accent-400">
              Architecture Highlight
            </span>
            <h2 className="font-heading text-2xl sm:text-3xl font-bold mt-2 mb-4">
              How Federated Learning Protects Your Data
            </h2>
            <p className="text-white/60 text-sm leading-relaxed mb-6">
              Traditional ed-tech uploads your full resume, GPA, and personal data to centralized cloud silos. SkillBridge runs decentralized training nodes across simulated university partitions:
            </p>

            <div className="space-y-3">
              <div className="flex items-center space-x-3 text-sm text-white/80">
                <span className="w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 flex items-center justify-center font-mono text-xs">1</span>
                <span>Your resume text and skills are parsed locally inside your college partition.</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-white/80">
                <span className="w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 flex items-center justify-center font-mono text-xs">2</span>
                <span>The client node trains a local gradient update using Flower & PyTorch.</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-white/80">
                <span className="w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 flex items-center justify-center font-mono text-xs">3</span>
                <span>Noise is added via Differential Privacy ($\epsilon = 0.85$), preventing model inversion.</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-base-800 text-center text-xs text-white/40">
        <p>© 2026 SkillBridge. Privacy Preserving Skill Gap Analysis using Federated Learning.</p>
      </footer>
    </div>
  );
}
