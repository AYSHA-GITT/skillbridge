import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import authService from '../services/authService';
import {
  TbSparkles,
  TbLock,
  TbEye,
  TbEyeOff,
  TbCheck,
  TbAlertCircle,
  TbArrowLeft,
  TbChecklist
} from 'react-icons/tb';

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [verifying, setVerifying] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [verifyError, setVerifyError] = useState('');

  const [form, setForm] = useState({
    new_password: '',
    confirm_password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setVerifying(false);
      setTokenValid(false);
      setVerifyError('No password reset token was provided in the URL.');
      return;
    }

    authService.verifyResetToken(token)
      .then((res) => {
        setTokenValid(true);
        setUserEmail(res.email || '');
      })
      .catch((err) => {
        setTokenValid(false);
        setVerifyError(
          err.response?.data?.error ||
          'This password reset link is invalid, expired, or has already been used.'
        );
      })
      .finally(() => {
        setVerifying(false);
      });
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');

    if (form.new_password.length < 8) {
      setSubmitError('New password must be at least 8 characters long.');
      return;
    }
    if (form.new_password !== form.confirm_password) {
      setSubmitError('New password and confirmation do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await authService.resetPassword(token, form.new_password, form.confirm_password);
      setResetSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 3500);
    } catch (err) {
      setSubmitError(
        err.response?.data?.error || 'Failed to reset password. Please request a new link.'
      );
    } finally {
      setSubmitting(false);
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
            Set New Password
          </h1>
          <p className="text-white/50 text-xs mt-1">
            Choose a strong, secure password for your SkillBridge account.
          </p>
        </div>

        {verifying ? (
          <div className="py-8 text-center text-white/50 text-xs flex flex-col items-center space-y-3">
            <div className="w-6 h-6 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin" />
            <span>Verifying password reset authorization...</span>
          </div>
        ) : !tokenValid ? (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs space-y-2">
              <div className="flex items-center space-x-2 font-semibold">
                <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>Invalid or Expired Link</span>
              </div>
              <p className="text-white/70 leading-relaxed">
                {verifyError}
              </p>
            </div>
            <Link
              to="/forgot-password"
              className="w-full py-3 rounded-xl btn-primary text-xs font-semibold flex items-center justify-center space-x-2"
            >
              <span>Request a New Reset Link</span>
            </Link>
            <div className="text-center pt-2">
              <Link to="/login" className="text-xs text-white/50 hover:text-white transition-colors">
                Back to Sign In
              </Link>
            </div>
          </div>
        ) : resetSuccess ? (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-teal-500/10 border border-teal-500/20 text-teal-300 text-xs space-y-2">
              <div className="flex items-center space-x-2 font-semibold text-teal-200">
                <TbCheck className="w-4 h-4 text-emerald-400" />
                <span>Password Reset Successful!</span>
              </div>
              <p className="text-white/80">
                Your password has been securely updated. Redirecting you to the sign-in page...
              </p>
            </div>
            <Link
              to="/login"
              className="w-full py-3 rounded-xl btn-primary text-xs font-semibold flex items-center justify-center space-x-2"
            >
              <span>Go to Sign In Immediately</span>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {userEmail && (
              <div className="px-3.5 py-2 rounded-xl bg-white/5 border border-white/10 text-xs flex items-center justify-between text-white/70">
                <span className="text-[11px] font-mono uppercase text-white/40">Account</span>
                <span className="font-semibold text-white">{userEmail}</span>
              </div>
            )}

            {submitError && (
              <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center space-x-2">
                <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                New Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="new_password"
                  placeholder="Minimum 8 characters"
                  className="input-field text-xs py-2.5 pl-9 pr-10"
                  value={form.new_password}
                  onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                  required
                />
                <TbLock className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-white/40 hover:text-white"
                >
                  {showPassword ? <TbEyeOff className="w-4 h-4" /> : <TbEye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                Confirm New Password
              </label>
              <div className="relative">
                <input
                  type={showConfirm ? 'text' : 'password'}
                  name="confirm_password"
                  placeholder="Repeat new password"
                  className="input-field text-xs py-2.5 pl-9 pr-10"
                  value={form.confirm_password}
                  onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
                  required
                />
                <TbLock className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-3 text-white/40 hover:text-white"
                >
                  {showConfirm ? <TbEyeOff className="w-4 h-4" /> : <TbEye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-1 text-[11px] text-white/50">
              <div className="flex items-center space-x-1.5">
                <TbChecklist className="w-3.5 h-3.5 text-accent-400" />
                <span>Password Requirements:</span>
              </div>
              <p className={`pl-5 ${form.new_password.length >= 8 ? 'text-emerald-400 font-medium' : 'text-white/40'}`}>
                • Minimum 8 characters ({form.new_password.length}/8)
              </p>
              <p className={`pl-5 ${form.new_password && form.new_password === form.confirm_password ? 'text-emerald-400 font-medium' : 'text-white/40'}`}>
                • Passwords match
              </p>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 rounded-xl font-semibold text-xs btn-primary shadow-glow transition-all flex items-center justify-center space-x-2 disabled:opacity-40"
            >
              <span>{submitting ? 'Updating Password...' : 'Save New Password & Sign In'}</span>
            </button>

            <div className="text-center pt-2">
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

