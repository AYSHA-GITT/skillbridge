import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { TbBuildingSkyscraper, TbShieldCheck, TbUser } from 'react-icons/tb';
import RecruiterLayout, { OrgBadge, useRecruiter } from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import { fmtDateTime } from '../../components/PassportBits';

const ORG_FIELDS = [
  ['name', 'Organisation name', 200],
  ['industry', 'Industry', 120],
  ['website', 'Website (https://...)', 300],
  ['contact_email', 'Hiring contact email', 120],
  ['contact_phone', 'Contact phone', 40],
  ['location', 'Location', 200],
  ['size', 'Size (e.g. 51-200 employees)', 40]
];

function Content() {
  const { me, refresh } = useRecruiter();
  const [params] = useSearchParams();
  const org = me.organisation;
  const [orgForm, setOrgForm] = useState({});
  const [profile, setProfile] = useState({});
  const [verify, setVerify] = useState({ registration_id: '', linkedin_url: '', proof_url: '', notes: '' });
  const [alert, setAlert] = useState(params.get('welcome')
    ? { type: 'success', message: 'Account created. Complete your organisation details and request verification.' } : null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setOrgForm({
      name: org.name, industry: org.industry, website: org.website, contact_email: org.contact_email,
      contact_phone: org.contact_phone, location: org.location, size: org.size, description: org.description
    });
    setProfile({ name: me.user.name, job_title: me.profile.job_title, phone: me.profile.phone });
  }, [me, org]);

  const run = async (fn, ok) => {
    setBusy(true);
    try {
      const res = await fn();
      await refresh();
      setAlert({ type: res?.verification_reset ? 'warning' : 'success', message: res?.message || ok });
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e) });
    } finally {
      setBusy(false);
    }
  };

  const canRequest = ['unverified', 'rejected'].includes(org.verification_status);

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="font-heading text-2xl font-bold text-white">Organisation</h1>
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}

      <section className="glass p-5 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-heading text-sm font-bold text-white flex items-center gap-2"><TbShieldCheck className="w-4 h-4 text-indigo-300" /> Verification</h2>
          <OrgBadge status={org.verification_status} />
        </div>
        <p className="text-xs text-white/55">
          An administrator checks that your organisation is real before you can publish jobs or search candidates.
          Students always see whether an employer is verified. Changing the organisation name or website after
          verification resets it.
        </p>
        {org.verification_note && (
          <p className="text-xs text-amber-200 bg-amber-500/5 border border-amber-500/30 rounded-xl p-3">Reviewer note: {org.verification_note}</p>
        )}
        {org.verification_status === 'pending' && (
          <p className="text-xs text-white/60">Requested {fmtDateTime(org.verification_requested_at)}. You will see the decision here.</p>
        )}
        {org.verification_status === 'verified' && (
          <p className="text-xs text-emerald-300">Verified on {fmtDateTime(org.verified_at)}.</p>
        )}
        {canRequest && (
          <form className="grid grid-cols-1 sm:grid-cols-2 gap-3"
            onSubmit={(e) => { e.preventDefault(); run(() => recruiterService.requestVerification(verify)); }}>
            <input className="input-field text-xs py-2.5" placeholder="Registration number (CIN / GSTIN / LLPIN)" maxLength={80}
              value={verify.registration_id} onChange={(e) => setVerify({ ...verify, registration_id: e.target.value })} />
            <input className="input-field text-xs py-2.5" placeholder="Company LinkedIn page (https://...)" maxLength={300}
              value={verify.linkedin_url} onChange={(e) => setVerify({ ...verify, linkedin_url: e.target.value })} />
            <input className="input-field text-xs py-2.5 sm:col-span-2" placeholder="Other proof link, e.g. careers page listing you (https://...)" maxLength={300}
              value={verify.proof_url} onChange={(e) => setVerify({ ...verify, proof_url: e.target.value })} />
            <textarea className="input-field text-xs py-2.5 sm:col-span-2" rows={2} placeholder="Notes for the reviewer (optional)" maxLength={1000}
              value={verify.notes} onChange={(e) => setVerify({ ...verify, notes: e.target.value })} />
            <button className="btn-primary text-xs py-2.5 sm:col-span-2" disabled={busy}>Request verification</button>
          </form>
        )}
      </section>

      <section className="glass p-5 space-y-4">
        <h2 className="font-heading text-sm font-bold text-white flex items-center gap-2"><TbBuildingSkyscraper className="w-4 h-4 text-indigo-300" /> Organisation profile</h2>
        <form className="grid grid-cols-1 sm:grid-cols-2 gap-3"
          onSubmit={(e) => { e.preventDefault(); run(() => recruiterService.updateOrganisation(orgForm)); }}>
          {ORG_FIELDS.map(([k, label, max]) => (
            <label key={k} className="text-[11px] text-white/50 space-y-1">
              <span>{label}</span>
              <input className="input-field text-xs py-2.5" maxLength={max} value={orgForm[k] || ''}
                onChange={(e) => setOrgForm({ ...orgForm, [k]: e.target.value })} required={k === 'name'} />
            </label>
          ))}
          <label className="text-[11px] text-white/50 space-y-1 sm:col-span-2">
            <span>About the organisation (shown to students)</span>
            <textarea className="input-field text-xs py-2.5" rows={3} maxLength={3000} value={orgForm.description || ''}
              onChange={(e) => setOrgForm({ ...orgForm, description: e.target.value })} />
          </label>
          <button className="btn-primary text-xs py-2.5 sm:col-span-2" disabled={busy}>Save organisation</button>
        </form>
      </section>

      <section className="glass p-5 space-y-4">
        <h2 className="font-heading text-sm font-bold text-white flex items-center gap-2"><TbUser className="w-4 h-4 text-indigo-300" /> Your recruiter profile</h2>
        <form className="grid grid-cols-1 sm:grid-cols-3 gap-3"
          onSubmit={(e) => { e.preventDefault(); run(() => recruiterService.updateProfile(profile)); }}>
          <input className="input-field text-xs py-2.5" placeholder="Name" required maxLength={100} value={profile.name || ''}
            onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
          <input className="input-field text-xs py-2.5" placeholder="Job title" maxLength={120} value={profile.job_title || ''}
            onChange={(e) => setProfile({ ...profile, job_title: e.target.value })} />
          <input className="input-field text-xs py-2.5" placeholder="Phone" maxLength={40} value={profile.phone || ''}
            onChange={(e) => setProfile({ ...profile, phone: e.target.value })} />
          <p className="text-[11px] text-white/40 sm:col-span-2">Signed in as {me.user.email}</p>
          <button className="btn-primary text-xs py-2.5" disabled={busy}>Save profile</button>
        </form>
      </section>
    </div>
  );
}

export default function RecruiterOrganisation() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
