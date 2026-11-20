import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  TbEye, TbEyeOff, TbShieldLock, TbBell, TbBuilding, TbRosetteDiscountCheck, TbMail, TbHistory, TbClipboardCheck
} from 'react-icons/tb';
import AppLayout from '../components/AppLayout';
import AlertBanner from '../components/AlertBanner';
import { candidateService, errorText } from '../services/recruiterService';
import { SECTION_LABELS, fmtDateTime, displaySkill } from '../components/PassportBits';

function Card({ title, icon: Icon, children, right }) {
  return (
    <section className="glass p-5 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-heading text-sm font-bold text-white flex items-center gap-2">
          {Icon && <Icon className="w-4 h-4 text-accent-400" />} {title}
        </h2>
        {right}
      </div>
      {children}
    </section>
  );
}

/** An employer asking the student to verify one skill; the student decides. */
export function VerificationRequestItem({ r, onRespond, busy }) {
  const [note, setNote] = useState('');
  const open = r.status === 'pending' || r.status === 'accepted';
  return (
    <div className={`surface p-3 text-xs space-y-1.5 ${r.seen ? '' : 'border-accent-400/40'}`}>
      <div className="flex flex-wrap items-center gap-2">
        <TbClipboardCheck className="w-4 h-4 text-accent-300" />
        <b className="text-white">{r.organisation?.name}</b>
        {r.organisation?.is_verified && <span className="text-[10px] text-emerald-300 flex items-center gap-0.5"><TbRosetteDiscountCheck className="w-3 h-3" />verified</span>}
        <span className="text-white/60">asked you to verify <b className="text-white">{displaySkill(r.skill_name)}</b>{r.job_title && <> for <b className="text-white">{r.job_title}</b></>}</span>
        <span className="text-white/35 ml-auto">{fmtDateTime(r.created_at)}</span>
      </div>
      {r.message && <p className="text-white/60 pl-6">"{r.message}"</p>}
      <div className="pl-6 space-y-1.5">
        <p className={r.status === 'completed' ? 'text-emerald-300' : r.status === 'accepted' ? 'text-sky-300' : 'text-white/50'}>
          {r.status_label}{r.completed_via_label && ` (${r.completed_via_label})`}
        </p>
        {r.close_reason && <p className="text-white/40">{r.close_reason}</p>}
        {r.status === 'pending' && (
          <>
            <p className="text-[11px] text-white/40">{r.what_is_shared}</p>
            {r.skill_verified && <p className="text-[11px] text-emerald-300/80">This skill is already verified - accepting tells the employer straight away.</p>}
            <input className="input-field text-xs py-1.5" maxLength={500} placeholder="Optional note to the employer"
              value={note} onChange={(e) => setNote(e.target.value)} />
            <div className="flex gap-2">
              <button disabled={busy} onClick={() => onRespond(r, 'accept', note)} className="btn-primary w-auto text-xs py-1.5 px-3 disabled:opacity-40">Accept</button>
              <button disabled={busy} onClick={() => onRespond(r, 'decline', note)} className="btn-ghost text-xs py-1.5">Decline</button>
            </div>
          </>
        )}
        {r.status === 'accepted' && !r.skill_verified && (
          <div className="flex flex-wrap gap-3">
            {r.skill_id && <Link to={`/verify-skill/${r.skill_id}`} className="text-accent-300">Take the assessment →</Link>}
            {r.skill_id && <Link to={`/skill-passport?evidence_for=${r.skill_id}`} className="text-accent-300">Submit evidence for review →</Link>}
            {!r.skill_id && <span className="text-white/40">This skill is no longer in your profile. Add it again on the Skill Passport page, or decline.</span>}
            <button disabled={busy} onClick={() => onRespond(r, 'decline', '')} className="text-white/40 hover:text-rose-300">Decline instead</button>
          </div>
        )}
        {open && r.status === 'accepted' && r.skill_status === 'pending_verification' && (
          <p className="text-[11px] text-white/40">Your evidence is waiting for a reviewer; the employer is told once it is accepted.</p>
        )}
      </div>
    </div>
  );
}

/** Student control centre for everything employers can see or have done. */
export default function EmployerAccess() {
  const [disc, setDisc] = useState(null);
  const [form, setForm] = useState(null);
  const [consent, setConsent] = useState(false);
  const [access, setAccess] = useState(null);
  const [updates, setUpdates] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [alert, setAlert] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, a, u, r] = await Promise.all([candidateService.getDiscovery(), candidateService.getAccess(),
        candidateService.getUpdates(), candidateService.readinessPreview()]);
      setDisc(d);
      setForm({ visibility: d.visibility, share_readiness: d.share_readiness });
      setAccess(a);
      setUpdates(u);
      setReadiness(r);
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e, 'Could not load employer access settings.') });
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async (enable) => {
    setSaving(true);
    try {
      const r = await candidateService.updateDiscovery({ is_discoverable: enable, consent: enable ? consent : undefined, ...form });
      setAlert({ type: 'success', message: r.message });
      setConsent(false);
      load();
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e) });
    } finally {
      setSaving(false);
    }
  };

  const [responding, setResponding] = useState(false);
  const respond = async (r, action, note) => {
    if (action === 'decline' && !window.confirm(`Decline the request to verify ${displaySkill(r.skill_name)}?`)) return;
    setResponding(true);
    try {
      const res = await candidateService.respondVerificationRequest(r.id, action, note);
      setAlert({ type: 'success', message: res.message });
      window.dispatchEvent(new Event('skillbridge:employerUpdatesChanged'));
      load();
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e) });
    } finally {
      setResponding(false);
    }
  };

  const markRead = async () => {
    await candidateService.markUpdatesRead().catch(() => {});
    window.dispatchEvent(new Event('skillbridge:employerUpdatesChanged'));
    load();
  };

  if (!disc || !form) {
    return <AppLayout>{alert ? <AlertBanner type={alert.type} message={alert.message} /> : <p className="text-sm text-white/40">Loading…</p>}</AppLayout>;
  }
  const toggleSection = (k) => setForm({ ...form, visibility: { ...form.visibility, sections: { ...form.visibility.sections, [k]: !form.visibility.sections[k] } } });

  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">Employer Access</h1>
          <p className="text-sm text-white/50 mt-1">Control what employers can see, and follow your applications to employer-posted jobs.</p>
        </div>
        {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}

        <Card title="Updates from employers" icon={TbBell}
          right={updates?.unread_count > 0 && <button onClick={markRead} className="text-[11px] text-accent-300">Mark {updates.unread_count} as read</button>}>
          {updates.invitations.length === 0 && updates.application_updates.length === 0
            && (updates.verification_requests || []).length === 0 && (
            <p className="text-xs text-white/40">No updates yet. Apply to an employer-posted job on the <Link to="/jobs" className="text-accent-300">Jobs page</Link>, or become visible to employers below.</p>
          )}
          {(updates.verification_requests || []).map((r) => (
            <VerificationRequestItem key={`v${r.id}`} r={r} onRespond={respond} busy={responding} />
          ))}
          {updates.invitations.map((i) => (
            <div key={`i${i.id}`} className={`surface p-3 text-xs space-y-1 ${i.seen ? '' : 'border-accent-400/40'}`}>
              <div className="flex flex-wrap items-center gap-2">
                <TbMail className="w-4 h-4 text-accent-300" />
                <b className="text-white">{i.organisation?.name}</b>
                {i.organisation?.is_verified && <span className="text-[10px] text-emerald-300 flex items-center gap-0.5"><TbRosetteDiscountCheck className="w-3 h-3" />verified</span>}
                <span className="text-white/60">invited you to apply for <b className="text-white">{i.job_title}</b></span>
                <span className="text-white/35 ml-auto">{fmtDateTime(i.created_at)}</span>
              </div>
              {i.message && <p className="text-white/60 pl-6">"{i.message}"</p>}
              <div className="pl-6">
                {i.applied ? <span className="text-emerald-300">You applied</span> : i.job_status === 'active'
                  ? <Link to={`/jobs?job=${i.job_id}`} className="text-accent-300">View the job and decide →</Link>
                  : <span className="text-white/40">This job is no longer open</span>}
              </div>
            </div>
          ))}
          {updates.application_updates.map((u) => (
            <div key={`u${u.id}`} className={`surface p-3 text-xs ${u.seen ? '' : 'border-accent-400/40'}`}>
              <div className="flex flex-wrap gap-2">
                <b className="text-white">{u.job_title}</b><span className="text-white/50">{u.company}</span>
                <span className="text-accent-300 font-semibold">{u.stage_label}</span>
                <span className="text-white/35 ml-auto">{fmtDateTime(u.created_at)}</span>
              </div>
              <p className="text-white/60 mt-1">{u.text}</p>
              {u.message && <p className="text-white/70 mt-1 border-l-2 border-accent-400/40 pl-2">Message from the employer: {u.message}</p>}
            </div>
          ))}
        </Card>

        <Card title="Visible to verified employers" icon={disc.is_discoverable ? TbEye : TbEyeOff}
          right={<span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${disc.is_discoverable ? 'text-emerald-300 border-emerald-500/40' : 'text-white/50 border-white/15'}`}>
            {disc.is_discoverable ? `On since ${fmtDateTime(disc.consent_at)}` : 'Off'}</span>}>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {[['Who can see it', disc.explanation.who], ['What they see', disc.explanation.what],
              ['Why', disc.explanation.why], ['How long', disc.explanation.how_long]].map(([k, v]) => (
              <div key={k} className="surface p-3"><dt className="text-white/40 mb-0.5">{k}</dt><dd className="text-white/75">{v}</dd></div>
            ))}
          </dl>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-white/40 font-semibold mb-2">Sections employers may see</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {disc.section_keys.map((k) => (
                <label key={k} className="flex items-center gap-2 text-xs text-white/75">
                  <input type="checkbox" checked={!!form.visibility.sections[k]} onChange={() => toggleSection(k)} /> {SECTION_LABELS[k]}
                </label>
              ))}
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 text-xs">
            <label className="flex items-center gap-2 text-white/75">Skills shown:
              <select className="input-field text-xs py-1.5 w-auto" value={form.visibility.skill_filter}
                onChange={(e) => setForm({ ...form, visibility: { ...form.visibility, skill_filter: e.target.value } })}>
                <option value="all">All skills (with their verification status)</option>
                <option value="evidence">Only skills with evidence or an assessment</option>
                <option value="verified">Only verified skills</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-white/75">
              <input type="checkbox" checked={form.share_readiness} onChange={(e) => setForm({ ...form, share_readiness: e.target.checked })} />
              Share my readiness score {readiness?.score != null && <span className="text-white/40">(currently {readiness.score}% · {readiness.label})</span>}
            </label>
          </div>
          <p className="text-[11px] text-white/40">Your email, phone number, resume file and uploaded evidence files are never shown in employer search.</p>
          <label className="flex items-start gap-2 text-xs text-white/75">
            <input type="checkbox" className="mt-0.5" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            I agree that recruiters from verified organisations may find me and see the sections selected above until I switch this off.
          </label>
          <div className="flex gap-2">
            <button disabled={saving || !consent} onClick={() => save(true)} className="btn-primary w-auto text-xs py-2 px-4 disabled:opacity-40">
              {disc.is_discoverable ? 'Save changes' : 'Make me visible'}
            </button>
            {disc.is_discoverable && (
              <button disabled={saving} onClick={() => save(false)} className="btn-ghost text-xs flex items-center gap-1"><TbEyeOff className="w-4 h-4" /> Hide me from employers</button>
            )}
          </div>
        </Card>

        <Card title="Employers with access through your applications" icon={TbBuilding}>
          {access.organisations_with_application_access.length === 0 ? (
            <p className="text-xs text-white/40">None. When you apply to an employer-posted job you choose what that employer sees.</p>
          ) : access.organisations_with_application_access.map((o) => (
            <div key={o.organisation} className="surface p-3 text-xs space-y-1">
              <div className="font-semibold text-white flex items-center gap-2">{o.organisation}
                {o.verified && <span className="text-[10px] text-emerald-300 flex items-center gap-0.5"><TbRosetteDiscountCheck className="w-3 h-3" />verified</span>}</div>
              {o.jobs.map((j) => (
                <div key={j.application_id} className="text-white/60">
                  {j.job_title} · {j.stage_label} · shared: {j.shared_sections.map((s) => SECTION_LABELS[s] || s).join(', ')} · since {fmtDateTime(j.shared_at)}
                </div>
              ))}
            </div>
          ))}
          <p className="text-[11px] text-white/40 flex items-center gap-1.5"><TbShieldLock className="w-3.5 h-3.5" /> {access.how_to_revoke}</p>
        </Card>

        <Card title="Who viewed my profile" icon={TbHistory}>
          {access.access_log.length === 0 ? <p className="text-xs text-white/40">No employer has opened your profile yet.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="text-left text-white/35"><th className="py-1.5 pr-3 font-medium">Organisation</th><th className="py-1.5 pr-3 font-medium">Through</th><th className="py-1.5 pr-3 font-medium">For job</th><th className="py-1.5 font-medium">When</th></tr></thead>
                <tbody className="divide-y divide-base-700/60">
                  {access.access_log.map((l, i) => (
                    <tr key={i}>
                      <td className="py-1.5 pr-3 text-white">{l.organisation} {l.organisation_verified && <TbRosetteDiscountCheck className="inline w-3.5 h-3.5 text-emerald-300" />}</td>
                      <td className="py-1.5 pr-3 text-white/60">{l.basis === 'application' ? 'Your application' : 'Employer search (you are visible)'}</td>
                      <td className="py-1.5 pr-3 text-white/60">{l.job_title || '—'}</td>
                      <td className="py-1.5 text-white/50">{fmtDateTime(l.at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
