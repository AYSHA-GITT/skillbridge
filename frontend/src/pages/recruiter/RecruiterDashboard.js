import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { TbBriefcase, TbUsers, TbUserSearch, TbArrowRight, TbAlertTriangle, TbRosetteDiscountCheck } from 'react-icons/tb';
import RecruiterLayout, { OrgBadge } from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import { fmtDate } from '../../components/PassportBits';

function Stat({ label, value, icon: Icon, to }) {
  const body = (
    <div className="surface p-4 flex items-center gap-3 hover:border-indigo-400/40 transition-colors">
      <Icon className="w-6 h-6 text-indigo-300" />
      <div>
        <div className="font-heading text-2xl font-bold text-white">{value ?? '—'}</div>
        <div className="text-[11px] text-white/50">{label}</div>
      </div>
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

function Content() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    recruiterService.dashboard().then(setData).catch((e) => setError(errorText(e, 'Could not load the dashboard.')));
  }, []);

  if (error) return <AlertBanner type="error" message={error} />;
  if (!data) return <p className="text-sm text-white/40">Loading…</p>;
  const org = data.organisation;
  const stages = data.pipeline_stages;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-white">Welcome, {data.user.name.split(' ')[0]}</h1>
        <p className="text-sm text-white/50 flex items-center gap-2 mt-1">{org.name} <OrgBadge status={org.verification_status} /></p>
      </div>

      {org.verification_status !== 'verified' && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <p className="text-sm text-amber-200 flex gap-2">
            <TbAlertTriangle className="w-5 h-5 flex-shrink-0" />
            {org.verification_status === 'pending'
              ? 'Your organisation is waiting for administrator verification. You can prepare job drafts meanwhile.'
              : 'Verify your organisation to publish jobs and search candidates. Until then you can prepare job drafts.'}
          </p>
          <Link to="/recruiter/organisation" className="btn-ghost text-xs whitespace-nowrap">Organisation & verification</Link>
        </div>
      )}

      {data.verification_requests?.unread > 0 && (
        <Link to="/recruiter/verifications" className="rounded-2xl border border-indigo-400/40 bg-indigo-500/10 p-4 flex items-center gap-2 text-sm text-indigo-200">
          <TbRosetteDiscountCheck className="w-5 h-5" />
          {data.verification_requests.unread} new answer{data.verification_requests.unread === 1 ? '' : 's'} to your skill verification requests
          <TbArrowRight className="ml-auto" />
        </Link>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Published jobs" value={data.jobs_by_status.active || 0} icon={TbBriefcase} to="/recruiter/jobs" />
        <Stat label="Drafts" value={data.jobs_by_status.draft || 0} icon={TbBriefcase} to="/recruiter/jobs" />
        <Stat label="Applications" value={data.applications_total} icon={TbUsers} to="/recruiter/pipeline" />
        <Stat label="Candidates open to employers" value={data.discoverable_candidates} icon={TbUserSearch} to="/recruiter/candidates" />
      </div>

      <div className="glass p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-sm font-bold text-white">Pipeline</h2>
          <Link to="/recruiter/pipeline" className="text-xs text-indigo-300 flex items-center gap-1">Open <TbArrowRight /></Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {stages.map((s) => (
            <div key={s.key} className="surface p-2.5 text-center">
              <div className="font-heading text-lg font-bold text-white">{data.applications_by_stage[s.key] || 0}</div>
              <div className="text-[10px] text-white/50 leading-tight">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="glass p-5 space-y-3">
        <h2 className="font-heading text-sm font-bold text-white">Recent applications</h2>
        {data.recent_applications.length === 0 ? (
          <p className="text-xs text-white/40">No applications yet. Publish a job, or invite candidates from search.</p>
        ) : (
          <div className="divide-y divide-base-700/60">
            {data.recent_applications.map((a) => (
              <Link key={a.application_id} to={`/recruiter/candidates/${a.candidate_ref}`}
                className="flex items-center justify-between py-2.5 text-xs hover:bg-white/5 px-2 rounded-lg">
                <span className="text-white font-medium">{a.name}</span>
                <span className="text-white/50">{a.job_title}</span>
                <span className="text-indigo-300">{a.stage_label}</span>
                <span className="text-white/40">{fmtDate(a.applied_at)}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function RecruiterDashboard() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
