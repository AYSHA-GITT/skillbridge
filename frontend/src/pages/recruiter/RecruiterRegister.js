import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TbBriefcase2 } from 'react-icons/tb';
import recruiterService, { errorText } from '../../services/recruiterService';

export default function RecruiterRegister() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '', email: '', password: '', job_title: '',
    org_name: '', industry: '', website: '', contact_email: '', location: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await recruiterService.register({
        name: form.name, email: form.email, password: form.password, job_title: form.job_title,
        organisation: {
          name: form.org_name, industry: form.industry, website: form.website.trim(),
          contact_email: form.contact_email, location: form.location
        }
      });
      navigate('/recruiter/organisation?welcome=1');
    } catch (err) {
      setError(errorText(err, 'Registration failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="glass w-full max-w-2xl p-8">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-400 to-violet-600 flex items-center justify-center text-white">
            <TbBriefcase2 className="w-5 h-5" />
          </div>
          <h1 className="font-heading text-2xl font-semibold">Create a recruiter account</h1>
        </div>
        <p className="text-white/50 text-sm mb-6">
          Hire students on verified skills. Your organisation starts as <b>unverified</b>: an administrator checks it
          before you can publish jobs or search candidates.
        </p>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
        )}

        <form onSubmit={submit} className="space-y-5">
          <fieldset className="space-y-3">
            <legend className="text-[11px] font-mono uppercase tracking-wider text-white/40 mb-2">You</legend>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input className="input-field text-sm" placeholder="Full name" value={form.name} onChange={set('name')} required maxLength={100} />
              <input className="input-field text-sm" placeholder="Your job title (e.g. Talent Acquisition Lead)" value={form.job_title} onChange={set('job_title')} maxLength={120} />
              <input type="email" className="input-field text-sm" placeholder="Work email" value={form.email} onChange={set('email')} required />
              <input type="password" className="input-field text-sm" placeholder="Password (8+ characters)" value={form.password} onChange={set('password')} required minLength={8} />
            </div>
            <p className="text-[11px] text-white/40">Use your company email: a matching website domain helps verification.</p>
          </fieldset>
          <fieldset className="space-y-3">
            <legend className="text-[11px] font-mono uppercase tracking-wider text-white/40 mb-2">Organisation</legend>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input className="input-field text-sm" placeholder="Organisation name" value={form.org_name} onChange={set('org_name')} required maxLength={200} />
              <input className="input-field text-sm" placeholder="Industry" value={form.industry} onChange={set('industry')} maxLength={120} />
              <input className="input-field text-sm" placeholder="Website (https://...)" value={form.website} onChange={set('website')} maxLength={300} />
              <input type="email" className="input-field text-sm" placeholder="Hiring contact email" value={form.contact_email} onChange={set('contact_email')} maxLength={120} />
              <input className="input-field text-sm sm:col-span-2" placeholder="Location (e.g. Bengaluru, Karnataka)" value={form.location} onChange={set('location')} maxLength={200} />
            </div>
          </fieldset>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating account...' : 'Create recruiter account'}
          </button>
        </form>
        <p className="text-center text-white/40 text-sm mt-6">
          Already registered? <Link to="/login?portal=recruiter" className="text-indigo-300 hover:text-indigo-200">Sign in</Link>
          {' · '}Student? <Link to="/register" className="text-accent-400 hover:text-accent-300">Student sign-up</Link>
        </p>
      </div>
    </div>
  );
}
