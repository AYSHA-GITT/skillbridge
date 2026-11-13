import React, { useState, useEffect, useRef } from 'react';
import AppLayout from '../components/AppLayout';
import AlertBanner from '../components/AlertBanner';
import authService from '../services/authService';
import {
  TbUser,
  TbSchool,
  TbBook,
  TbCalendar,
  TbCamera,
  TbLock,
  TbEye,
  TbEyeOff,
  TbCheck,
  TbShieldLock,
  TbMail,
  TbBriefcase,
  TbSparkles,
  TbInfoCircle,
  TbCircleCheck
} from 'react-icons/tb';

export default function ProfileSettings() {
  const [loading, setLoading] = useState(true);
  const [profileSaving, setProfileSaving] = useState(false);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);

  const [alert, setAlert] = useState(null);
  const [passwordAlert, setPasswordAlert] = useState(null);

  const fileInputRef = useRef(null);

  // Profile Information Form State
  const [profileForm, setProfileForm] = useState({
    name: '',
    email: '',
    college: '',
    course: '',
    year: '',
    target_career: '',
    role: 'student',
    profile_photo: null,
    created_at: null,
    readiness_score: 0
  });

  // Password Management Form State
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Fetch student details from database
  const loadProfile = async () => {
    setLoading(true);
    try {
      const student = await authService.getCurrentUser();
      if (student) {
        setProfileForm({
          name: student.name || '',
          email: student.email || '',
          college: student.college || '',
          course: student.course || '',
          year: student.year || '1st Year',
          target_career: student.target_career || '',
          role: student.role || 'student',
          profile_photo: student.profile_photo || null,
          created_at: student.created_at || null,
          readiness_score: student.readiness_score || 0
        });
      }
    } catch {
      setAlert({ type: 'error', message: 'Failed to load your profile details from the server.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  // Handle Profile Form Changes
  const handleProfileChange = (e) => {
    setProfileForm({ ...profileForm, [e.target.name]: e.target.value });
  };

  // Submit Profile Information Changes
  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setAlert(null);
    setProfileSaving(true);

    try {
      const res = await authService.updateProfile({
        name: profileForm.name,
        college: profileForm.college,
        course: profileForm.course,
        year: profileForm.year,
        target_career: profileForm.target_career
      });

      const updated = res.student;
      setProfileForm((prev) => ({
        ...prev,
        name: updated.name,
        college: updated.college,
        course: updated.course,
        year: updated.year,
        target_career: updated.target_career
      }));

      // Broadcast update across the whole application immediately
      window.dispatchEvent(new CustomEvent('skillbridge:profileUpdated', { detail: updated }));

      setAlert({
        type: 'success',
        message: 'Profile information updated successfully! Changes are saved to your account.'
      });
    } catch (err) {
      setAlert({
        type: 'error',
        message: err.response?.data?.error || 'Unable to update profile. Please verify your entries.'
      });
    } finally {
      setProfileSaving(false);
    }
  };

  // Handle Profile Photo Selection & Upload
  const handlePhotoSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (max 3MB)
    if (file.size > 3 * 1024 * 1024) {
      setAlert({ type: 'error', message: 'Photo file size exceeds the 3MB limit.' });
      return;
    }

    setPhotoUploading(true);
    setAlert(null);

    try {
      const res = await authService.uploadProfilePhoto(file);
      const updatedPhotoUrl = res.profile_photo;
      const updatedStudent = res.student;

      setProfileForm((prev) => ({
        ...prev,
        profile_photo: updatedPhotoUrl
      }));

      // Reflect photo change across entire app immediately (Navbar, etc.)
      window.dispatchEvent(new CustomEvent('skillbridge:profileUpdated', { detail: updatedStudent }));

      setAlert({
        type: 'success',
        message: 'Profile photo uploaded and updated successfully!'
      });
    } catch (err) {
      setAlert({
        type: 'error',
        message: err.response?.data?.error || 'Failed to upload profile photo.'
      });
    } finally {
      setPhotoUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Submit Password Change
  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordAlert(null);

    if (passwordForm.new_password.length < 8) {
      setPasswordAlert({ type: 'error', message: 'New password must be at least 8 characters long.' });
      return;
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordAlert({ type: 'error', message: 'New password and confirmation do not match.' });
      return;
    }

    setPasswordSaving(true);
    try {
      await authService.changePassword(
        passwordForm.current_password,
        passwordForm.new_password,
        passwordForm.confirm_password
      );

      setPasswordAlert({
        type: 'success',
        message: 'Your password has been changed successfully.'
      });

      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
    } catch (err) {
      setPasswordAlert({
        type: 'error',
        message: err.response?.data?.error || 'Failed to change password. Verify your current password.'
      });
    } finally {
      setPasswordSaving(false);
    }
  };

  const avatarUrl = profileForm.profile_photo
    ? profileForm.profile_photo.startsWith('http')
      ? profileForm.profile_photo
      : `http://127.0.0.1:5000${profileForm.profile_photo}`
    : null;

  return (
    <AppLayout>
      <div className="space-y-6 animate-fade-in pb-12">
        {/* Header */}
        <div>
          <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
            Profile Settings
          </h1>
          <p className="text-white/60 text-xs mt-1">
            Manage your personal academic identity, profile photo, and account security credentials.
          </p>
        </div>

        {/* Informational Banner */}
        <div className="glass p-4 rounded-2xl border border-teal-500/20 bg-teal-950/15 flex items-start space-x-3">
          <TbInfoCircle className="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-white/70 space-y-1">
            <p className="font-semibold text-teal-200">
              Verified Institutional Identity
            </p>
            <p>
              Your academic year, college, and target career are used to benchmark your Skill Readiness score and match recommended opportunities.
            </p>
          </div>
        </div>

        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {loading ? (
          <div className="glass p-12 text-center text-white/50 text-xs flex flex-col items-center space-y-3">
            <div className="w-6 h-6 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin" />
            <span>Loading profile settings from database...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* LEFT COLUMN: Profile Information Form (2 Cols) */}
            <div className="lg:col-span-2 space-y-6">
              {/* Profile Details Card */}
              <div className="glass p-6 rounded-2xl border border-base-700/60 space-y-6">
                <div className="flex items-center space-x-2.5 pb-4 border-b border-base-700/60">
                  <TbUser className="w-5 h-5 text-accent-400" />
                  <h2 className="font-heading text-base font-bold text-white">
                    Personal & Academic Information
                  </h2>
                </div>

                {/* Avatar Uploader Section */}
                <div className="flex flex-col sm:flex-row items-center space-y-4 sm:space-y-0 sm:space-x-5 p-4 rounded-xl bg-white/5 border border-white/10">
                  <div className="relative group">
                    {avatarUrl ? (
                      <img
                        src={avatarUrl}
                        alt={profileForm.name}
                        className="w-20 h-20 rounded-full object-cover border-2 border-accent-400/50 shadow-md"
                      />
                    ) : (
                      <div className="w-20 h-20 rounded-full bg-gradient-to-br from-accent-500/20 to-teal-500/20 border-2 border-accent-400/40 flex items-center justify-center text-accent-300 font-bold text-2xl">
                        {profileForm.name ? profileForm.name[0].toUpperCase() : 'S'}
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={photoUploading}
                      title="Upload new profile photo"
                      className="absolute inset-0 rounded-full bg-black/60 opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center text-white transition-opacity text-[10px] font-medium"
                    >
                      <TbCamera className="w-5 h-5 mb-0.5" />
                      <span>{photoUploading ? 'Uploading...' : 'Change'}</span>
                    </button>
                  </div>

                  <div className="text-center sm:text-left space-y-1.5 flex-1">
                    <p className="text-sm font-semibold text-white">Profile Photo</p>
                    <p className="text-xs text-white/50">
                      Supports JPG, PNG, WEBP or GIF (Max 3MB). This photo will appear in your navbar and student badges.
                    </p>
                    <div>
                      <input
                        type="file"
                        ref={fileInputRef}
                        accept="image/png,image/jpeg,image/webp,image/gif"
                        className="hidden"
                        onChange={handlePhotoSelect}
                      />
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={photoUploading}
                        className="px-3 py-1.5 rounded-xl border border-accent-400/30 text-xs font-semibold text-accent-300 bg-accent-500/10 hover:bg-accent-500/20 transition-all inline-flex items-center space-x-1.5 disabled:opacity-40"
                      >
                        <TbCamera className="w-3.5 h-3.5" />
                        <span>{photoUploading ? 'Uploading Photo...' : 'Upload New Photo'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Edit Fields Form */}
                <form onSubmit={handleProfileSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Full Name */}
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                        Full Name <span className="text-accent-400">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          name="name"
                          required
                          value={profileForm.name}
                          onChange={handleProfileChange}
                          placeholder="Your full name"
                          className="input-field text-xs py-2.5 pl-9"
                        />
                        <TbUser className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                      </div>
                    </div>

                    {/* Email (Read-Only) */}
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                        Email Address (Account ID)
                      </label>
                      <div className="relative">
                        <input
                          type="email"
                          disabled
                          value={profileForm.email}
                          className="input-field text-xs py-2.5 pl-9 opacity-60 cursor-not-allowed bg-base-900"
                        />
                        <TbMail className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                      </div>
                    </div>

                    {/* College / University */}
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                        College / University
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          name="college"
                          value={profileForm.college}
                          onChange={handleProfileChange}
                          placeholder="e.g. Stanford University"
                          className="input-field text-xs py-2.5 pl-9"
                        />
                        <TbSchool className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                      </div>
                    </div>

                    {/* Degree / Course */}
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                        Degree / Major Course
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          name="course"
                          value={profileForm.course}
                          onChange={handleProfileChange}
                          placeholder="e.g. B.Tech Computer Science"
                          className="input-field text-xs py-2.5 pl-9"
                        />
                        <TbBook className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                      </div>
                    </div>

                    {/* Academic Year */}
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                        Academic Year
                      </label>
                      <div className="relative">
                        <select
                          name="year"
                          value={profileForm.year}
                          onChange={handleProfileChange}
                          className="input-field text-xs py-2.5 pl-9 appearance-none bg-base-900"
                        >
                          <option value="1st Year">1st Year</option>
                          <option value="2nd Year">2nd Year</option>
                          <option value="3rd Year">3rd Year</option>
                          <option value="4th Year">4th Year</option>
                          <option value="5th Year / Dual Degree">5th Year / Dual Degree</option>
                          <option value="Postgraduate / Masters">Postgraduate / Masters</option>
                          <option value="Recent Graduate / Alumni">Recent Graduate / Alumni</option>
                        </select>
                        <TbCalendar className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                      </div>
                    </div>

                    {/* Target Career Track */}
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                        Target Career Track
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          name="target_career"
                          value={profileForm.target_career}
                          onChange={handleProfileChange}
                          placeholder="e.g. Full Stack Developer, AI Engineer"
                          className="input-field text-xs py-2.5 pl-9"
                        />
                        <TbBriefcase className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 flex justify-end">
                    <button
                      type="submit"
                      disabled={profileSaving}
                      className="px-6 py-2.5 rounded-xl font-semibold text-xs btn-primary shadow-glow transition-all flex items-center space-x-2 disabled:opacity-40"
                    >
                      <TbCheck className="w-4 h-4" />
                      <span>{profileSaving ? 'Saving Changes...' : 'Save Profile Changes'}</span>
                    </button>
                  </div>
                </form>
              </div>

              {/* Security & Password Card */}
              <div className="glass p-6 rounded-2xl border border-base-700/60 space-y-6">
                <div className="flex items-center space-x-2.5 pb-4 border-b border-base-700/60">
                  <TbShieldLock className="w-5 h-5 text-teal-400" />
                  <div>
                    <h2 className="font-heading text-base font-bold text-white">
                      Password & Security
                    </h2>
                    <p className="text-white/50 text-xs">
                      Update your account password with cryptographic verification.
                    </p>
                  </div>
                </div>

                {passwordAlert && (
                  <AlertBanner
                    type={passwordAlert.type}
                    message={passwordAlert.message}
                    onClose={() => setPasswordAlert(null)}
                  />
                )}

                <form onSubmit={handlePasswordSubmit} className="space-y-4">
                  {/* Current Password */}
                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                      Current Password <span className="text-accent-400">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type={showCurrentPassword ? 'text' : 'password'}
                        name="current_password"
                        required
                        value={passwordForm.current_password}
                        onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                        placeholder="••••••••"
                        className="input-field text-xs py-2.5 pl-9 pr-10"
                      />
                      <TbLock className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                      <button
                        type="button"
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        className="absolute right-3 top-3 text-white/40 hover:text-white"
                      >
                        {showCurrentPassword ? <TbEyeOff className="w-4 h-4" /> : <TbEye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* New Password */}
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                        New Password <span className="text-accent-400">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showNewPassword ? 'text' : 'password'}
                          name="new_password"
                          required
                          value={passwordForm.new_password}
                          onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                          placeholder="Min. 8 characters"
                          className="input-field text-xs py-2.5 pl-9 pr-10"
                        />
                        <TbLock className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                        <button
                          type="button"
                          onClick={() => setShowNewPassword(!showNewPassword)}
                          className="absolute right-3 top-3 text-white/40 hover:text-white"
                        >
                          {showNewPassword ? <TbEyeOff className="w-4 h-4" /> : <TbEye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {/* Confirm Password */}
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-white/50 mb-1.5">
                        Confirm New Password <span className="text-accent-400">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showConfirmPassword ? 'text' : 'password'}
                          name="confirm_password"
                          required
                          value={passwordForm.confirm_password}
                          onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                          placeholder="Repeat new password"
                          className="input-field text-xs py-2.5 pl-9 pr-10"
                        />
                        <TbLock className="w-4 h-4 text-white/40 absolute left-3 top-3 pointer-events-none" />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          className="absolute right-3 top-3 text-white/40 hover:text-white"
                        >
                          {showConfirmPassword ? <TbEyeOff className="w-4 h-4" /> : <TbEye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="submit"
                      disabled={passwordSaving}
                      className="px-6 py-2.5 rounded-xl font-semibold text-xs border border-teal-500/30 text-teal-300 bg-teal-500/15 hover:bg-teal-500/25 transition-all flex items-center space-x-2 disabled:opacity-40 shadow-glow"
                    >
                      <TbShieldLock className="w-4 h-4" />
                      <span>{passwordSaving ? 'Updating Password...' : 'Change Password'}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>

            {/* RIGHT COLUMN: Account Summary & Privacy Meta */}
            <div className="space-y-6">
              {/* Account Overview Card */}
              <div className="glass p-5 rounded-2xl border border-base-700/60 space-y-4">
                <div className="flex items-center space-x-2 text-white">
                  <TbSparkles className="w-4 h-4 text-accent-400" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-white/60">
                    Account Overview
                  </span>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="flex justify-between items-center py-2 border-b border-base-700/40">
                    <span className="text-white/50">Account Role</span>
                    <span className="font-mono px-2 py-0.5 rounded bg-accent-500/15 text-accent-300 border border-accent-400/30 capitalize">
                      {profileForm.role}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-2 border-b border-base-700/40">
                    <span className="text-white/50">Readiness Score</span>
                    <span className="font-bold text-accent-400">
                      {Math.round(profileForm.readiness_score || 0)}%
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-2 border-b border-base-700/40">
                    <span className="text-white/50">Member Since</span>
                    <span className="text-white/80 font-mono text-[11px]">
                      {profileForm.created_at
                        ? new Date(profileForm.created_at).toLocaleDateString(undefined, {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric'
                          })
                        : 'Active Member'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Data & Security Guarantees Card */}
              <div className="surface p-4 rounded-2xl border border-teal-500/30 bg-teal-950/20 space-y-2.5">
                <div className="flex items-center space-x-2 text-teal-400">
                  <TbShieldLock className="w-4 h-4 flex-shrink-0" />
                  <span className="text-xs font-semibold">Security & Privacy Commitments</span>
                </div>
                <div className="space-y-2 text-[11px] text-white/70">
                  <div className="flex items-start space-x-2">
                    <TbCircleCheck className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>Passwords hashed using industry-standard Werkzeug scrypt/pbkdf2 cryptography.</span>
                  </div>
                  <div className="flex items-start space-x-2">
                    <TbCircleCheck className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>Profile photos stored securely with randomized safe filenames.</span>
                  </div>
                  <div className="flex items-start space-x-2">
                    <TbCircleCheck className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>Password reset tokens are single-use and time-limited to 60 minutes.</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

