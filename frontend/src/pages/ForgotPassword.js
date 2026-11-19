import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import authService from '../services/authService';
import { TbSparkles, TbMail, TbArrowLeft, TbCheck, TbAlertCircle } from 'react-icons/tb';
import { apiErrorMessage } from '../utils/apiErrors';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const res = await authService.forgotPassword(email);
      setSubmitted(true);
      // The server answers the same way whether or not the address has an account.
      setMessage(res.message || 'If an account exists for this email address, we have sent it a password reset link.');
    } catch (err) {
      setError(apiErrorMessage(err, 'Unable to process the request. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-base-950">
      <div className="w-full max-w-md p-8 rounded-3xl glass">
        {/* Brand */}
        <div className="mb-6">
          <div className="flex items-center space-x-2.5 mb-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-400 to-teal-600 flex items-center justify-center text-base-950 font-bold">
              <TbSparkles className="w-4 h-4" />
            </div>
            <span className="font-heading font-bold text-lg text-white">SkillBridge</span>
          </div>
          <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
            Reset Password
          </h1>
          <p className="text-white/50 text-xs mt-1">
            Enter the email address you registered with (student, recruiter or administrator account). We will email you a link to choose a new password.
          </p>
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center space-x-2">
            <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {submitted ? (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs space-y-2">
              <div className="flex items-center space-x-2 font-semibold text-teal-200">
                <TbCheck className="w-4 h-4 text-emerald-400" />
                <span>Check your email</span>
              </div>
              <p className="text-white/80 leading-relaxed">
                {message}
              </p>
              <p className="text-[11px] text-white/50">
                Look in your inbox and spam folder. The link works once and expires in 60 minutes. Only the newest link you request will work.
              </p>
            </div>

            <button
              type="button"
              onClick={() => { setSubmitted(false); setMessage(''); }}
              className="w-full py-2.5 rounded-xl text-white/60 hover:text-white text-xs font-semibold transition-colors"
            >
              Didn't get it? Send another link
            </button>

            <div className="pt-2">
              <Link
                to="/login"
                className="w-full py-2.5 rounded-xl border border-base-700 hover:border-base-600 text-white/80 hover:text-white text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
              >
                <TbArrowLeft className="w-4 h-4" />
                <span>Return to Sign In</span>
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                Registered Email Address
              </label>
              <div className="relative">
                <input
                  type="email"
                  name="email"
                  placeholder="student@university.edu"
                  className="input-field text-xs py-2.5 pl-9"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <TbMail className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl font-semibold text-xs btn-primary shadow-glow transition-all flex items-center justify-center space-x-2 disabled:opacity-40"
            >
              <span>{loading ? 'Sending...' : 'Send Password Reset Link'}</span>
            </button>

            <div className="pt-2 text-center">
              <Link
                to="/login"
                className="inline-flex items-center space-x-1.5 text-xs text-white/50 hover:text-white transition-colors"
              >
                <TbArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Sign In</span>
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

