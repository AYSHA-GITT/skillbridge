import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { TbRosetteDiscountCheck, TbShieldLock } from 'react-icons/tb';
import RecruiterLayout from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import { displaySkill, fmtDateTime } from '../../components/PassportBits';
import { VR_STATUS_STYLES } from './RecruiterCandidateProfile';

const FILTERS = [['', 'All'], ['open', 'Open'], ['completed', 'Verified'], ['declined', 'Declined'],
  ['cancelled', 'Cancelled'], ['closed', 'Closed']];

/** Every skill verification request the organisation has sent, with the candidate's answer. */
export function VerificationList({ requests, onCancel }) {
  if (requests.length === 0) {
    return <p className="text-xs text-white/40">No requests yet. Open a candidate's profile and choose "Request verification" for skills they have not verified.</p>;
  }
  return (
    <div className="space-y-2">
      {requests.map((r) => (
        <div key={r.id} className={`surface p-3 text-xs space-y-1 ${r.unread ? 'border-indigo-400/50' : ''}`}>
          <div className="flex flex-wrap items-center gap-2">
            <b className="text-white">{displaySkill(r.skill_name)}</b>
            <span className={`text-[10px] px-2 py-0.5 rounded-full border ${VR_STATUS_STYLES[r.status] || ''}`}>{r.status_label}</span>
            {r.unread && <span className="text-[10px] text-indigo-300 font-semibold">New</span>}
            {r.candidate_ref ? (
              <Link to={`/recruiter/candidates/${r.candidate_ref}`} className="text-indigo-300">{r.candidate_name}</Link>
            ) : (
              <span className="text-white/40 flex items-center gap-1"><TbShieldLock className="w-3.5 h-3.5" /> Candidate no longer shares their profile</span>
            )}
            {r.job_title && <span className="text-white/40">for {r.job_title}</span>}
            <span className="text-white/35 ml-auto">Requested {fmtDateTime(r.created_at)}</span>
          </div>
          {r.completed_via_label && (
            <p className="text-emerald-300/90">Verified {fmtDateTime(r.completed_at)}: {r.completed_via_label}.</p>
          )}
          {r.student_note && <p className="text-white/60">Candidate's note: "{r.student_note}"</p>}
          {r.close_reason && <p className="text-white/45">{r.close_reason}</p>}
          {(r.status === 'pending' || r.status === 'accepted') && onCancel && (
            <button className="text-[11px] text-white/40 hover:text-rose-300" onClick={() => onCancel(r)}>Cancel request</button>
          )}
        </div>
      ))}
    </div>
  );
}

function Content() {
  const [status, setStatus] = useState('');
  const [data, setData] = useState(null);
  const [alert, setAlert] = useState(null);

  const load = useCallback(() => recruiterService.verificationRequests(status).then(setData)
    .catch((e) => setAlert({ type: 'error', message: errorText(e, 'Could not load verification requests.') })), [status]);
  useEffect(() => { load(); }, [load]);

  const markRead = async () => {
    await recruiterService.markVerificationRequestsRead().catch(() => {});
    load();
  };
  const cancel = async (r) => {
    if (!window.confirm(`Cancel the request for ${displaySkill(r.skill_name)}?`)) return;
    try {
      const res = await recruiterService.cancelVerificationRequest(r.id);
      setAlert({ type: 'success', message: res.message });
      load();
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e) });
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-heading text-2xl font-bold text-white flex items-center gap-2">
          <TbRosetteDiscountCheck className="w-6 h-6 text-indigo-300" /> Verification requests
        </h1>
        <p className="text-sm text-white/50 mt-1">Skills you asked candidates to verify. A request is completed only when the skill passes a SkillBridge assessment or a reviewer accepts the candidate's evidence.</p>
      </div>
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}
      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map(([k, label]) => (
          <button key={k} onClick={() => setStatus(k)}
            className={`text-[11px] px-3 py-1 rounded-full border ${status === k ? 'border-indigo-400 text-indigo-200 bg-indigo-500/15' : 'border-base-700 text-white/55'}`}>
            {label}
          </button>
        ))}
        {data?.unread > 0 && <button onClick={markRead} className="ml-auto text-[11px] text-indigo-300">Mark {data.unread} update{data.unread === 1 ? '' : 's'} as read</button>}
      </div>
      {!data ? <p className="text-sm text-white/40">Loading…</p> : <VerificationList requests={data.requests} onCancel={cancel} />}
    </div>
  );
}

export default function RecruiterVerifications() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
