import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import AlertBanner from '../components/AlertBanner';
import passportService from '../services/passportService';
import {
  StatusBadge,
  ReviewBadge,
  StatusLegend,
  SafeLink,
  KIND_LABELS,
  SECTION_LABELS,
  GROUP_ORDER,
  STATUS_ORDER,
  fmtDate,
  fmtDateTime,
  displaySkill
} from '../components/PassportBits';
import {
  TbId,
  TbSchool,
  TbBrandLinkedin,
  TbBrandGithub,
  TbWorld,
  TbPlus,
  TbTrash,
  TbPencil,
  TbUpload,
  TbDownload,
  TbSend,
  TbFileImport,
  TbShare,
  TbQrcode,
  TbCopy,
  TbBan,
  TbHistory,
  TbFileTypePdf,
  TbClipboardCheck,
  TbTarget,
  TbChevronDown,
  TbChevronUp,
  TbLock,
  TbFileUpload
} from 'react-icons/tb';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'skills', label: 'Skills & Verification' },
  { id: 'evidence', label: 'Projects & Evidence' },
  { id: 'share', label: 'Share & Export' }
];

const EMPTY_EVIDENCE = {
  kind: 'project',
  title: '',
  organization: '',
  description: '',
  url: '',
  start_date: '',
  end_date: '',
  skill_ids: []
};

const errMsg = (e, fallback) => e?.response?.data?.error || fallback;

const svgDataUri = (svg) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;

function Card({ title, icon: Icon, action, children, className = '' }) {
  return (
    <section className={`glass p-5 rounded-2xl space-y-3 ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-heading text-sm font-bold text-white flex items-center gap-2">
            {Icon && <Icon className="w-4 h-4 text-accent-400" />}
            {title}
          </h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

function Empty({ children }) {
  return <p className="text-xs text-white/40 italic">{children}</p>;
}

export default function SkillPassport() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('overview');
  const [alert, setAlert] = useState(null);

  const load = useCallback(async () => {
    try {
      setData(await passportService.getMyPassport());
    } catch (e) {
      setAlert({ type: 'error', message: errMsg(e, 'Could not load your Skill Passport.') });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const notify = (type, message) => setAlert({ type, message });

  if (loading) {
    return (
      <AppLayout>
        <div className="text-white/40 text-sm font-mono">Loading Skill Passport…</div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-white flex items-center gap-2">
              <TbId className="w-6 h-6 text-accent-400" />
              Verified Skill Passport
            </h1>
            <p className="text-white/50 text-sm mt-1 max-w-2xl">
              An evidence-backed record of what you know and can do. Skills only become <b className="text-emerald-300">Verified</b> through
              a SkillBridge assessment or a reviewed piece of evidence — never from a resume mention or an upload alone.
            </p>
          </div>
        </div>

        {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}

        {data && (
          <>
            <div className="flex gap-1 overflow-x-auto overflow-y-hidden border-b border-base-700/60">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-4 py-2.5 text-xs font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors ${
                    tab === t.id ? 'border-accent-400 text-accent-300' : 'border-transparent text-white/50 hover:text-white'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {tab === 'overview' && <OverviewTab data={data} reload={load} notify={notify} navigate={navigate} />}
            {tab === 'skills' && (
              <SkillsTab
                data={data}
                reload={load}
                notify={notify}
                navigate={navigate}
                onAddEvidence={() => setTab('evidence')}
              />
            )}
            {tab === 'evidence' && <EvidenceTab data={data} reload={load} notify={notify} />}
            {tab === 'share' && <ShareTab data={data} reload={load} notify={notify} />}
          </>
        )}
      </div>
    </AppLayout>
  );
}

/* ───────────────────────────── Overview ───────────────────────────── */
function OverviewTab({ data, reload, notify, navigate }) {
  const [editing, setEditing] = useState(!data.profile_saved);
  const [form, setForm] = useState(data.profile);
  const [saving, setSaving] = useState(false);
  const sug = data.suggestions || {};
  const st = data.student;
  const ci = data.career_interests || {};

  const fillFromResume = () =>
    setForm((f) => ({
      ...f,
      summary: f.summary || sug.summary || '',
      linkedin_url: f.linkedin_url || sug.linkedin_url || '',
      github_url: f.github_url || sug.github_url || '',
      portfolio_url: f.portfolio_url || sug.portfolio_url || ''
    }));
  const hasSuggestions = sug.summary || sug.linkedin_url || sug.github_url || sug.portfolio_url;

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await passportService.updateProfile(form);
      notify('success', 'Professional profile saved.');
      setEditing(false);
      reload();
    } catch (err) {
      notify('error', errMsg(err, 'Could not save the profile.'));
    } finally {
      setSaving(false);
    }
  };

  const counts = data.status_counts || {};
  const total = data.skills.length;

  return (
    <div className="space-y-5">
      {/* Identity header */}
      <div className="glass p-6 rounded-2xl flex flex-col md:flex-row md:items-start gap-5">
        <div className="w-14 h-14 rounded-2xl bg-accent-500/15 border border-accent-400/30 flex items-center justify-center font-heading text-xl font-bold text-accent-300 flex-shrink-0">
          {(st.name || '?').slice(0, 1).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0 space-y-1">
          <h2 className="font-heading text-xl font-bold text-white">{st.name}</h2>
          <p className="text-sm text-accent-300">{data.profile.headline || <span className="text-white/30 italic">Add a headline below</span>}</p>
          <p className="text-xs text-white/50 flex items-center gap-1.5">
            <TbSchool className="w-3.5 h-3.5" />
            {[st.course, st.college, st.year].filter(Boolean).join(' · ') || 'Education not set — update it in Profile Settings'}
          </p>
          <div className="flex flex-wrap gap-3 pt-1 text-xs">
            {data.profile.linkedin_url && (
              <SafeLink href={data.profile.linkedin_url} className="text-sky-300 flex items-center gap-1">
                <TbBrandLinkedin className="w-4 h-4" /> LinkedIn
              </SafeLink>
            )}
            {data.profile.github_url && (
              <SafeLink href={data.profile.github_url} className="text-white/70 flex items-center gap-1">
                <TbBrandGithub className="w-4 h-4" /> GitHub
              </SafeLink>
            )}
            {data.profile.portfolio_url && (
              <SafeLink href={data.profile.portfolio_url} className="text-accent-300 flex items-center gap-1">
                <TbWorld className="w-4 h-4" /> Portfolio
              </SafeLink>
            )}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center md:w-72 flex-shrink-0">
          <div className="surface p-3">
            <div className="font-heading text-2xl font-bold text-emerald-300">{counts.verified || 0}</div>
            <div className="text-[10px] text-white/50">Verified</div>
          </div>
          <div className="surface p-3">
            <div className="font-heading text-2xl font-bold text-amber-300">
              {(counts.pending_verification || 0) + (counts.evidence_submitted || 0) + (counts.assessment_completed || 0)}
            </div>
            <div className="text-[10px] text-white/50">In progress</div>
          </div>
          <div className="surface p-3">
            <div className="font-heading text-2xl font-bold text-white">{total}</div>
            <div className="text-[10px] text-white/50">Total skills</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Professional profile */}
        <Card
          title="Professional profile"
          icon={TbId}
          action={
            !editing && (
              <button onClick={() => { setForm(data.profile); setEditing(true); }} className="btn-ghost text-xs py-1 flex items-center gap-1">
                <TbPencil className="w-3.5 h-3.5" /> Edit
              </button>
            )
          }
        >
          {editing ? (
            <form onSubmit={save} className="space-y-3">
              {hasSuggestions && (
                <button type="button" onClick={fillFromResume} className="text-[11px] text-accent-300 hover:text-white flex items-center gap-1">
                  <TbFileImport className="w-3.5 h-3.5" /> Fill empty fields from my resume
                </button>
              )}
              <input className="input-field text-sm" maxLength={160} placeholder="Headline, e.g. Final-year CSE student focused on data engineering"
                value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} />
              <textarea className="input-field text-sm min-h-[110px]" maxLength={2000} placeholder="Short professional summary"
                value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
              <input className="input-field text-sm" placeholder="https://linkedin.com/in/…" value={form.linkedin_url}
                onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })} />
              <input className="input-field text-sm" placeholder="https://github.com/…" value={form.github_url}
                onChange={(e) => setForm({ ...form, github_url: e.target.value })} />
              <input className="input-field text-sm" placeholder="https://your-portfolio…" value={form.portfolio_url}
                onChange={(e) => setForm({ ...form, portfolio_url: e.target.value })} />
              <p className="text-[10px] text-white/40 flex items-center gap-1">
                <TbLock className="w-3 h-3" /> Your email and phone number are never included in shared passports.
              </p>
              <div className="flex gap-2">
                <button type="submit" disabled={saving} className="btn-primary text-xs py-2 w-auto px-5">
                  {saving ? 'Saving…' : 'Save profile'}
                </button>
                {data.profile_saved && (
                  <button type="button" onClick={() => setEditing(false)} className="btn-ghost text-xs">Cancel</button>
                )}
              </div>
            </form>
          ) : data.profile.summary ? (
            <p className="text-sm text-white/70 whitespace-pre-line leading-relaxed">{data.profile.summary}</p>
          ) : (
            <Empty>No summary yet.</Empty>
          )}
        </Card>

        {/* Education */}
        <Card title="Education" icon={TbSchool}
          action={<button onClick={() => navigate('/profile-settings')} className="text-[11px] text-white/50 hover:text-white">Edit in Profile Settings</button>}>
          {data.education.current.institution || data.education.current.program ? (
            <div className="surface p-3">
              <div className="text-sm font-semibold text-white">{data.education.current.program || 'Program not set'}</div>
              <div className="text-xs text-white/50">
                {[data.education.current.institution, data.education.current.year].filter(Boolean).join(' · ')}
              </div>
              <div className="text-[10px] text-white/30 mt-1">From your SkillBridge profile</div>
            </div>
          ) : (
            <Empty>Add your college and course in Profile Settings.</Empty>
          )}
          {data.education.from_resume.map((e, i) => (
            <div key={i} className="surface p-3">
              <div className="text-sm text-white/90">{e.degree || e.institution}</div>
              <div className="text-xs text-white/50">{[e.degree ? e.institution : '', e.year, e.score].filter(Boolean).join(' · ')}</div>
              <div className="text-[10px] text-white/30 mt-1">Detected in your resume</div>
            </div>
          ))}
        </Card>

        {/* Career interests */}
        <Card title="Career interests" icon={TbTarget}
          action={<button onClick={() => navigate('/jobs')} className="text-[11px] text-white/50 hover:text-white">Edit job preferences</button>}>
          <dl className="text-xs space-y-2">
            <div className="flex gap-2"><dt className="text-white/40 w-28 flex-shrink-0">Target career</dt><dd className="text-white/80">{ci.target_career || '—'}</dd></div>
            <div className="flex gap-2"><dt className="text-white/40 w-28 flex-shrink-0">Preferred roles</dt><dd className="text-white/80">{ci.preferred_roles?.join(', ') || '—'}</dd></div>
            <div className="flex gap-2"><dt className="text-white/40 w-28 flex-shrink-0">Locations</dt><dd className="text-white/80">{ci.preferred_locations?.join(', ') || '—'}</dd></div>
            <div className="flex gap-2"><dt className="text-white/40 w-28 flex-shrink-0">Work modes</dt><dd className="text-white/80">{ci.work_modes?.join(', ') || '—'}</dd></div>
            <div className="flex gap-2"><dt className="text-white/40 w-28 flex-shrink-0">Job types</dt><dd className="text-white/80">{ci.job_types?.join(', ') || '—'}</dd></div>
          </dl>
        </Card>

        {/* Assessments */}
        <Card title="Skill assessment results" icon={TbClipboardCheck}
          action={<button onClick={() => navigate('/assessment')} className="text-[11px] text-white/50 hover:text-white">Take an assessment</button>}>
          {data.assessments.length === 0 ? (
            <Empty>No assessments taken yet.</Empty>
          ) : (
            <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
              {data.assessments.map((a) => (
                <div key={a.skill_name} className="flex items-center justify-between text-xs surface px-3 py-2">
                  <span className="text-white/80">{displaySkill(a.skill_name)}</span>
                  <span className="flex items-center gap-3">
                    <span className={a.passed ? 'text-emerald-300 font-semibold' : 'text-amber-300'}>
                      {Math.round(a.score_percent)}% ({a.correct}/{a.total})
                    </span>
                    <span className="text-white/35 w-24 text-right">{fmtDate(a.taken_at)}</span>
                  </span>
                </div>
              ))}
            </div>
          )}
          <p className="text-[10px] text-white/35">Pass mark: {data.pass_threshold}%. The latest attempt for each skill is shown.</p>
        </Card>
      </div>

      <Card title="What the statuses mean">
        <StatusLegend labels={data.status_labels} descriptions={data.status_descriptions} />
      </Card>
    </div>
  );
}

/* ───────────────────────────── Skills ───────────────────────────── */
function SkillsTab({ data, reload, notify, navigate, onAddEvidence }) {
  const [filter, setFilter] = useState('all');
  const [newSkill, setNewSkill] = useState('');
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(null);

  const addSkill = async (e) => {
    e.preventDefault();
    if (!newSkill.trim()) return;
    setBusy(true);
    try {
      await passportService.addSkill(newSkill.trim());
      notify('success', `Added "${newSkill.trim()}" as a self-declared skill. Add evidence or take an assessment to strengthen it.`);
      setNewSkill('');
      reload();
    } catch (err) {
      notify('error', errMsg(err, 'Could not add the skill.'));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (s) => {
    if (!window.confirm(`Remove the self-declared skill "${displaySkill(s.skill_name)}"?`)) return;
    try {
      await passportService.removeSkill(s.id);
      reload();
    } catch (err) {
      notify('error', errMsg(err, 'Could not remove the skill.'));
    }
  };

  const shown = data.skills.filter((s) => filter === 'all' || s.status === filter);

  return (
    <div className="space-y-5">
      <div className="flex flex-col lg:flex-row gap-3 lg:items-center justify-between">
        <div className="flex flex-wrap gap-1.5">
          {['all', ...STATUS_ORDER].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`text-[11px] px-3 py-1.5 rounded-full border transition-colors ${
                filter === s ? 'border-accent-400 text-accent-300 bg-accent-500/10' : 'border-base-700 text-white/50 hover:text-white'
              }`}
            >
              {s === 'all' ? 'All' : data.status_labels[s]} ({s === 'all' ? data.skills.length : data.status_counts[s] || 0})
            </button>
          ))}
        </div>
        <form onSubmit={addSkill} className="flex gap-2">
          <input className="input-field text-xs py-2 sm:w-64" maxLength={60} placeholder="Add a skill (self-declared)"
            value={newSkill} onChange={(e) => setNewSkill(e.target.value)} />
          <button disabled={busy} className="btn-primary text-xs py-2 w-auto px-3 flex items-center gap-1"><TbPlus className="w-4 h-4" />Add</button>
        </form>
      </div>

      {data.skills.length === 0 && (
        <div className="glass p-6 rounded-2xl text-center space-y-3">
          <p className="text-sm text-white/60">No skills yet. Upload your resume to extract them, or add one above.</p>
          <button onClick={() => navigate('/upload-resume')} className="btn-primary text-xs py-2 w-auto px-5 inline-flex items-center gap-2">
            <TbFileUpload className="w-4 h-4" /> Upload resume
          </button>
        </div>
      )}

      {GROUP_ORDER.map((g) => {
        const rows = shown.filter((s) => s.group === g);
        if (!rows.length) return null;
        return (
          <Card key={g} title={data.skill_groups[g]}>
            <div className="divide-y divide-base-700/60">
              {rows.map((s) => {
                const isOpen = open === s.id;
                return (
                  <div key={s.id} className="py-3">
                    <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-4">
                      <button onClick={() => setOpen(isOpen ? null : s.id)} className="flex items-center gap-2 text-left flex-1 min-w-0">
                        {isOpen ? <TbChevronUp className="w-4 h-4 text-white/40" /> : <TbChevronDown className="w-4 h-4 text-white/40" />}
                        <span className="text-sm font-semibold text-white truncate">{displaySkill(s.skill_name)}</span>
                        <StatusBadge status={s.status} label={s.status_label} title={data.status_descriptions[s.status]} />
                      </button>
                      <div className="grid grid-cols-3 gap-3 text-[11px] md:w-[360px]">
                        <div><div className="text-white/35">Proficiency</div><div className="text-white/80">{s.proficiency}</div></div>
                        <div>
                          <div className="text-white/35">Assessment</div>
                          <div className={s.assessment ? (s.assessment.passed ? 'text-emerald-300' : 'text-amber-300') : 'text-white/40'}>
                            {s.assessment ? `${Math.round(s.assessment.score_percent)}%` : '—'}
                          </div>
                        </div>
                        <div><div className="text-white/35">Last verified</div><div className="text-white/80">{fmtDate(s.last_verified_at)}</div></div>
                      </div>
                    </div>

                    {isOpen && (
                      <div className="mt-3 ml-6 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="surface p-3 space-y-2">
                          <div className="text-white/40 font-semibold uppercase text-[10px] tracking-wider">Supporting evidence</div>
                          <div className="flex flex-wrap gap-1.5">
                            {s.signals.map((sig) => <StatusBadge key={sig} status={sig} label={data.status_labels[sig]} />)}
                          </div>
                          {s.resume_evidence && (
                            <div>
                              <div className="text-white/70">
                                Resume — {String(s.resume_evidence.evidence_strength).replace('_', ' ')}
                                {s.resume_evidence.sections.length > 0 && ` (${s.resume_evidence.sections.join(', ')})`}
                              </div>
                              {s.resume_evidence.snippets.map((sn, i) => (
                                <p key={i} className="text-white/40 italic mt-1">“{sn.snippet}”</p>
                              ))}
                            </div>
                          )}
                          {s.assessment && (
                            <div className="text-white/70">
                              SkillBridge assessment: {s.assessment.correct}/{s.assessment.total} correct ({Math.round(s.assessment.score_percent)}%) on {fmtDate(s.assessment.taken_at)}
                            </div>
                          )}
                          {s.evidence.map((e) => (
                            <div key={e.id} className="flex items-center justify-between gap-2">
                              <span className="text-white/70">{KIND_LABELS[e.kind]}: {e.title}</span>
                              <ReviewBadge status={e.review_status} />
                            </div>
                          ))}
                          {!s.resume_evidence && !s.assessment && s.evidence.length === 0 && <Empty>No evidence yet.</Empty>}
                        </div>
                        <div className="surface p-3 space-y-2">
                          <div className="text-white/40 font-semibold uppercase text-[10px] tracking-wider">Confidence signals</div>
                          {s.confidence.resume_mention_confidence != null && (
                            <div className="text-white/70">
                              Resume mention certainty: {Math.round(s.confidence.resume_mention_confidence * 100)}%
                              <div className="text-[10px] text-white/35">Rule-based: how sure we are the resume refers to this skill. It does not measure ability.</div>
                            </div>
                          )}
                          {s.confidence.verification_score != null && (
                            <div className="text-white/70">
                              Verification score: {Math.round(s.confidence.verification_score * 100)}%
                              <div className="text-[10px] text-white/35">75% assessment result + 25% resume evidence strength.</div>
                            </div>
                          )}
                          {s.confidence.resume_mention_confidence == null && s.confidence.verification_score == null && (
                            <Empty>No confidence measurement for this skill yet.</Empty>
                          )}
                          <div className="flex flex-wrap gap-2 pt-1">
                            <button onClick={() => navigate(`/verify-skill/${s.id}`)} className="btn-ghost text-[11px] py-1 flex items-center gap-1">
                              <TbClipboardCheck className="w-3.5 h-3.5" /> {s.assessment ? 'Retake assessment' : 'Take assessment'}
                            </button>
                            <button onClick={onAddEvidence} className="btn-ghost text-[11px] py-1 flex items-center gap-1">
                              <TbPlus className="w-3.5 h-3.5" /> Add evidence
                            </button>
                            {s.source === 'self_declared' && !s.assessment && !s.resume_evidence && (
                              <button onClick={() => remove(s)} className="btn-ghost text-[11px] py-1 flex items-center gap-1 hover:text-rose-300">
                                <TbTrash className="w-3.5 h-3.5" /> Remove
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        );
      })}

      <Card title="What the statuses mean">
        <StatusLegend labels={data.status_labels} descriptions={data.status_descriptions} />
      </Card>
    </div>
  );
}

/* ───────────────────────────── Evidence ───────────────────────────── */
function EvidenceTab({ data, reload, notify }) {
  const [form, setForm] = useState(null); // null = closed; {id?: number, ...fields}
  const [saving, setSaving] = useState(false);
  const [selectedImports, setSelectedImports] = useState({});
  const [importing, setImporting] = useState(false);

  const candidates = data.resume_import_candidates || {};
  const candidateCount = ['project', 'certificate', 'experience']
    .reduce((n, k) => n + (candidates[k] || []).filter((c) => !c.already_added).length, 0);

  const startNew = () => setForm({ ...EMPTY_EVIDENCE });
  const startEdit = (e) =>
    setForm({
      id: e.id,
      kind: e.kind,
      title: e.title,
      organization: e.organization,
      description: e.description,
      url: e.url,
      start_date: e.start_date,
      end_date: e.end_date,
      skill_ids: e.skills.map((s) => s.id)
    });

  const toggleSkill = (id) =>
    setForm((f) => ({ ...f, skill_ids: f.skill_ids.includes(id) ? f.skill_ids.filter((x) => x !== id) : [...f.skill_ids, id] }));

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { id, ...payload } = form;
      if (id) {
        const res = await passportService.updateEvidence(id, payload);
        notify(res.review_reset ? 'warning' : 'success', res.message);
      } else {
        await passportService.createEvidence(payload);
        notify('success', 'Evidence added. Request verification when it is ready to be reviewed.');
      }
      setForm(null);
      reload();
    } catch (err) {
      notify('error', errMsg(err, 'Could not save the evidence.'));
    } finally {
      setSaving(false);
    }
  };

  const act = async (fn, okMsg) => {
    try {
      const res = await fn();
      notify('success', okMsg || res?.message);
      reload();
    } catch (err) {
      notify('error', errMsg(err, 'Something went wrong.'));
    }
  };

  const doImport = async () => {
    const items = Object.entries(selectedImports)
      .filter(([, v]) => v)
      .map(([k]) => {
        const [kind, index] = k.split(':');
        return { kind, index: Number(index) };
      });
    if (!items.length) return;
    setImporting(true);
    try {
      const res = await passportService.importFromResume(items);
      notify('success', res.message);
      setSelectedImports({});
      reload();
    } catch (err) {
      notify('error', errMsg(err, 'Import failed.'));
    } finally {
      setImporting(false);
    }
  };

  const byKind = useMemo(() => {
    const out = {};
    data.evidence.forEach((e) => {
      (out[e.kind] = out[e.kind] || []).push(e);
    });
    return out;
  }, [data.evidence]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row justify-between gap-3 sm:items-center">
        <p className="text-xs text-white/50 max-w-xl">
          Link projects, certificates, experience and practical challenges to your skills. Evidence counts as
          <b className="text-violet-300"> submitted</b> until a reviewer accepts it; editing reviewed evidence resets its review.
        </p>
        <button onClick={startNew} className="btn-primary text-xs py-2 w-auto px-4 flex items-center gap-1.5">
          <TbPlus className="w-4 h-4" /> Add evidence
        </button>
      </div>

      {form && (
        <Card title={form.id ? 'Edit evidence' : 'New evidence'}>
          <form onSubmit={save} className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <select className="input-field text-sm" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                {Object.entries(KIND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <input className="input-field text-sm" required maxLength={200} placeholder="Title"
                value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              <input className="input-field text-sm" maxLength={200}
                placeholder={form.kind === 'certificate' ? 'Issuer' : form.kind === 'experience' ? 'Organization' : form.kind === 'practical_challenge' ? 'Platform (e.g. Kaggle)' : 'Organization (optional)'}
                value={form.organization} onChange={(e) => setForm({ ...form, organization: e.target.value })} />
              <input className="input-field text-sm" maxLength={500} placeholder="Link (repository, demo, credential URL…)"
                value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
              <input className="input-field text-sm" maxLength={20} placeholder="Start (e.g. 2025-06)"
                value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
              <input className="input-field text-sm" maxLength={20} placeholder="End (or Present)"
                value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            </div>
            <textarea className="input-field text-sm min-h-[90px]" maxLength={2000} placeholder="What did you do and what was the outcome?"
              value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <div>
              <div className="text-[11px] text-white/50 mb-1.5">Skills this demonstrates</div>
              {data.skills.length === 0 ? (
                <Empty>Add skills first (Skills & Verification tab).</Empty>
              ) : (
                <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
                  {data.skills.map((s) => (
                    <button type="button" key={s.id} onClick={() => toggleSkill(s.id)}
                      className={`text-[11px] px-2.5 py-1 rounded-full border ${
                        form.skill_ids.includes(s.id) ? 'border-accent-400 bg-accent-500/15 text-accent-300' : 'border-base-700 text-white/50 hover:text-white'
                      }`}>
                      {displaySkill(s.skill_name)}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <button disabled={saving} className="btn-primary text-xs py-2 w-auto px-5">{saving ? 'Saving…' : 'Save'}</button>
              <button type="button" onClick={() => setForm(null)} className="btn-ghost text-xs">Cancel</button>
            </div>
          </form>
        </Card>
      )}

      {candidateCount > 0 && (
        <Card title="Found in your resume" icon={TbFileImport}
          action={
            <button onClick={doImport} disabled={importing || !Object.values(selectedImports).some(Boolean)}
              className="btn-primary text-xs py-1.5 w-auto px-4 disabled:opacity-40">
              {importing ? 'Importing…' : 'Import selected'}
            </button>
          }>
          <p className="text-[11px] text-white/45">
            Select items to add to your passport — nothing from your resume is shared until you import it.
            {data.resume && ` Source: ${data.resume.filename}.`}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {['project', 'certificate', 'experience'].flatMap((kind) =>
              (candidates[kind] || []).filter((c) => !c.already_added).map((c) => {
                const key = `${kind}:${c.index}`;
                return (
                  <label key={key} className="surface p-3 flex items-start gap-2 cursor-pointer text-xs">
                    <input type="checkbox" className="mt-0.5 accent-teal-400" checked={!!selectedImports[key]}
                      onChange={(e) => setSelectedImports({ ...selectedImports, [key]: e.target.checked })} />
                    <span className="min-w-0">
                      <span className="text-white/40">{KIND_LABELS[kind]} · </span>
                      <span className="text-white/90">{c.title}</span>
                      {c.organization && <span className="text-white/50"> — {c.organization}</span>}
                      {c.description && <span className="block text-white/40 line-clamp-2 mt-0.5">{c.description}</span>}
                    </span>
                  </label>
                );
              })
            )}
          </div>
        </Card>
      )}

      {data.evidence.length === 0 && !form && <Empty>No evidence added yet.</Empty>}

      {Object.entries(KIND_LABELS).map(([kind, label]) =>
        (byKind[kind] || []).length ? (
          <Card key={kind} title={`${label}s`}>
            <div className="space-y-3">
              {byKind[kind].map((e) => (
                <div key={e.id} className="surface p-4 space-y-2">
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-white">{e.title}</div>
                      <div className="text-xs text-white/50">
                        {[e.organization, [e.start_date, e.end_date].filter(Boolean).join(' – ')].filter(Boolean).join(' · ')}
                        {e.source === 'resume' && <span className="ml-1 text-white/30">(imported from resume)</span>}
                      </div>
                    </div>
                    <ReviewBadge status={e.review_status} />
                  </div>
                  {e.description && <p className="text-xs text-white/60 whitespace-pre-line">{e.description}</p>}
                  {e.url && <SafeLink href={e.url} className="text-xs text-accent-300">{e.url}</SafeLink>}
                  <div className="flex flex-wrap gap-1">
                    {e.skills.map((s) => (
                      <span key={s.id} className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-white/60">{displaySkill(s.skill_name)}</span>
                    ))}
                    {e.skills.length === 0 && <span className="text-[10px] text-amber-300/80">No skills linked</span>}
                  </div>
                  {e.review_status === 'rejected' && e.review_note && (
                    <p className="text-[11px] text-rose-300">Reviewer note: {e.review_note}</p>
                  )}
                  {e.review_status === 'verified' && (
                    <p className="text-[11px] text-emerald-300/80">Accepted on {fmtDate(e.reviewed_at)}{e.review_note ? ` — ${e.review_note}` : ''}</p>
                  )}
                  <div className="flex flex-wrap gap-2 pt-1">
                    <button onClick={() => startEdit(e)} className="btn-ghost text-[11px] py-1 flex items-center gap-1"><TbPencil className="w-3.5 h-3.5" />Edit</button>
                    <label className="btn-ghost text-[11px] py-1 flex items-center gap-1 cursor-pointer">
                      <TbUpload className="w-3.5 h-3.5" />{e.has_file ? 'Replace file' : 'Attach file'}
                      <input type="file" accept=".pdf,.png,.jpg,.jpeg" className="hidden"
                        onChange={(ev) => {
                          const f = ev.target.files?.[0];
                          ev.target.value = '';
                          if (f) act(() => passportService.uploadEvidenceFile(e.id, f), 'File attached. Files stay private: recruiters never see them.');
                        }} />
                    </label>
                    {e.has_file && (
                      <button onClick={() => passportService.downloadEvidenceFile(e.id, e.original_filename).catch(() => notify('error', 'Download failed.'))}
                        className="btn-ghost text-[11px] py-1 flex items-center gap-1"><TbDownload className="w-3.5 h-3.5" />{e.original_filename || 'File'}</button>
                    )}
                    {(e.review_status === 'not_requested' || e.review_status === 'rejected') && (
                      <button onClick={() => act(() => passportService.requestReview(e.id), 'Submitted for verification.')}
                        className="btn-ghost text-[11px] py-1 flex items-center gap-1 text-amber-300"><TbSend className="w-3.5 h-3.5" />Request verification</button>
                    )}
                    <button onClick={() => window.confirm('Delete this evidence?') && act(() => passportService.deleteEvidence(e.id), 'Evidence deleted.')}
                      className="btn-ghost text-[11px] py-1 flex items-center gap-1 hover:text-rose-300"><TbTrash className="w-3.5 h-3.5" />Delete</button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ) : null
      )}
    </div>
  );
}

/* ───────────────────────────── Share & export ───────────────────────────── */
const EXPIRY_OPTIONS = [
  { days: 1, label: '1 day' },
  { days: 7, label: '7 days' },
  { days: 30, label: '30 days' },
  { days: 90, label: '90 days' },
  { days: 180, label: '180 days' }
];

function ShareTab({ data, reload, notify }) {
  const [sections, setSections] = useState(() =>
    Object.fromEntries(data.section_keys.map((k) => [k, true]))
  );
  const [skillFilter, setSkillFilter] = useState('all');
  const [label, setLabel] = useState('');
  const [days, setDays] = useState(30);
  const [allowPdf, setAllowPdf] = useState(true);
  const [consent, setConsent] = useState(false);
  const [creating, setCreating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [created, setCreated] = useState(null);
  const [logs, setLogs] = useState({});

  const chosen = Object.keys(sections).filter((k) => sections[k]);

  const create = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await passportService.createShare({
        label,
        expires_in_days: days,
        allow_pdf: allowPdf,
        consent,
        visibility: { sections, skill_filter: skillFilter }
      });
      setCreated(res);
      setConsent(false);
      setLabel('');
      reload();
    } catch (err) {
      notify('error', errMsg(err, 'Could not create the link.'));
    } finally {
      setCreating(false);
    }
  };

  const exportPdf = async () => {
    setExporting(true);
    try {
      await passportService.exportPdf(chosen, skillFilter);
    } catch {
      notify('error', 'PDF export failed.');
    } finally {
      setExporting(false);
    }
  };

  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      notify('success', 'Link copied to clipboard.');
    } catch {
      notify('warning', 'Copy failed — select the link and copy it manually.');
    }
  };

  const downloadQr = () =>
    passportService.downloadBlob(new Blob([created.qr_svg], { type: 'image/svg+xml' }), 'SkillPassport_QR.svg');

  const revoke = async (s) => {
    if (!window.confirm(`Revoke "${s.label || 'this link'}"? Anyone using it will lose access immediately.`)) return;
    try {
      await passportService.revokeShare(s.id);
      notify('success', 'Link revoked.');
      reload();
    } catch (err) {
      notify('error', errMsg(err, 'Could not revoke the link.'));
    }
  };

  const toggleLog = async (id) => {
    if (logs[id]) {
      setLogs((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      return;
    }
    try {
      setLogs({ ...logs, [id]: await passportService.getAccessLog(id) });
    } catch {
      notify('error', 'Could not load access history.');
    }
  };

  const EVENT_LABELS = { view: 'Viewed', pdf: 'Downloaded PDF', denied_expired: 'Blocked (expired)', denied_revoked: 'Blocked (revoked)', denied_inactive: 'Blocked (account inactive)' };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <Card title="Choose what recruiters can see" icon={TbShare} className="lg:col-span-3">
          <form onSubmit={create} className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              {data.section_keys.map((k) => (
                <label key={k} className="flex items-center gap-2 text-xs text-white/70 cursor-pointer">
                  <input type="checkbox" className="accent-teal-400" checked={!!sections[k]}
                    onChange={(e) => setSections({ ...sections, [k]: e.target.checked })} />
                  {SECTION_LABELS[k] || k}
                </label>
              ))}
            </div>
            <div className="space-y-1">
              <div className="text-[11px] text-white/50">Skills to include</div>
              {[
                ['all', 'All skills, with their verification status'],
                ['evidence', 'Only skills with evidence or an assessment'],
                ['verified', 'Only verified skills']
              ].map(([v, l]) => (
                <label key={v} className="flex items-center gap-2 text-xs text-white/70 cursor-pointer">
                  <input type="radio" name="skillFilter" className="accent-teal-400" checked={skillFilter === v} onChange={() => setSkillFilter(v)} />
                  {l}
                </label>
              ))}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input className="input-field text-sm" maxLength={120} placeholder="Label, e.g. Acme internship"
                value={label} onChange={(e) => setLabel(e.target.value)} />
              <select className="input-field text-sm" value={days} onChange={(e) => setDays(Number(e.target.value))}>
                {EXPIRY_OPTIONS.map((o) => <option key={o.days} value={o.days}>Expires in {o.label}</option>)}
              </select>
            </div>
            <label className="flex items-center gap-2 text-xs text-white/70 cursor-pointer">
              <input type="checkbox" className="accent-teal-400" checked={allowPdf} onChange={(e) => setAllowPdf(e.target.checked)} />
              Allow viewers to download a PDF copy
            </label>
            <label className="flex items-start gap-2 text-xs text-white/80 cursor-pointer surface p-3">
              <input type="checkbox" className="accent-teal-400 mt-0.5" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>
                I consent to anyone with this link seeing the sections selected above until it expires or I revoke it.
                My email, phone number, resume file and uploaded evidence files are never shared.
              </span>
            </label>
            <div className="flex flex-wrap gap-2">
              <button disabled={creating || !consent || chosen.length === 0} className="btn-primary text-xs py-2 w-auto px-5 disabled:opacity-40 flex items-center gap-1.5">
                <TbQrcode className="w-4 h-4" />{creating ? 'Creating…' : 'Create link & QR code'}
              </button>
              <button type="button" onClick={exportPdf} disabled={exporting || chosen.length === 0}
                className="btn-ghost text-xs flex items-center gap-1.5 disabled:opacity-40">
                <TbFileTypePdf className="w-4 h-4" />{exporting ? 'Preparing…' : 'Export PDF (these sections)'}
              </button>
            </div>
          </form>
        </Card>

        <Card title="Your new link" icon={TbQrcode} className="lg:col-span-2">
          {created ? (
            <div className="space-y-3">
              <div className="bg-white rounded-xl p-3 w-48 mx-auto">
                <img src={svgDataUri(created.qr_svg)} alt="QR code for the share link" className="w-full h-auto" />
              </div>
              <div className="surface p-2 text-[11px] text-white/80 break-all font-mono">{created.url}</div>
              <div className="flex flex-wrap gap-2">
                <button onClick={() => copy(created.url)} className="btn-ghost text-xs flex items-center gap-1"><TbCopy className="w-3.5 h-3.5" />Copy link</button>
                <button onClick={downloadQr} className="btn-ghost text-xs flex items-center gap-1"><TbDownload className="w-3.5 h-3.5" />Download QR</button>
              </div>
              <p className="text-[11px] text-amber-300/90">
                Save this link now. For security only a fingerprint of it is stored, so it cannot be shown again — create a new link if you lose it.
              </p>
            </div>
          ) : (
            <Empty>Create a link to get its URL and QR code here.</Empty>
          )}
        </Card>
      </div>

      <Card title="Share links & access history" icon={TbHistory}>
        {data.shares.length === 0 ? (
          <Empty>No links created yet.</Empty>
        ) : (
          <div className="space-y-2">
            {data.shares.map((s) => (
              <div key={s.id} className="surface p-3 text-xs space-y-2">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-semibold text-white truncate">
                      {s.label || 'Untitled link'} <span className="font-mono text-white/30">…{s.token_hint}</span>
                    </div>
                    <div className="text-white/45">
                      Created {fmtDate(s.created_at)} · {s.status === 'active' ? 'Expires' : 'Expired/ended'} {fmtDate(s.expires_at)} ·
                      {' '}{s.access_count} view{s.access_count === 1 ? '' : 's'}
                      {s.last_accessed_at && ` · last ${fmtDateTime(s.last_accessed_at)}`}
                    </div>
                    <div className="text-white/35 mt-0.5">
                      Shows: {Object.keys(s.visibility.sections || {}).filter((k) => s.visibility.sections[k]).map((k) => SECTION_LABELS[k]).join(', ')}
                      {' '}· skills: {s.visibility.skill_filter}{s.allow_pdf ? ' · PDF allowed' : ''}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`px-2 py-0.5 rounded-full border text-[10px] ${
                      s.status === 'active' ? 'text-emerald-300 border-emerald-500/40' : 'text-white/40 border-white/15'
                    }`}>{s.status}</span>
                    <button onClick={() => toggleLog(s.id)} className="btn-ghost text-[11px] py-1 flex items-center gap-1">
                      <TbHistory className="w-3.5 h-3.5" />History
                    </button>
                    {s.status === 'active' && (
                      <button onClick={() => revoke(s)} className="btn-ghost text-[11px] py-1 flex items-center gap-1 hover:text-rose-300">
                        <TbBan className="w-3.5 h-3.5" />Revoke
                      </button>
                    )}
                  </div>
                </div>
                {logs[s.id] && (
                  <div className="border-t border-base-700/60 pt-2 space-y-1">
                    <div className="text-white/45">{logs[s.id].unique_viewers} distinct viewer(s). {logs[s.id].note}</div>
                    {logs[s.id].access_log.length === 0 ? (
                      <Empty>No one has opened this link yet.</Empty>
                    ) : (
                      <div className="max-h-48 overflow-y-auto space-y-1">
                        {logs[s.id].access_log.map((l) => (
                          <div key={l.id} className="flex flex-wrap gap-x-3 text-[11px] text-white/60">
                            <span className="w-36">{fmtDateTime(l.accessed_at)}</span>
                            <span className={l.event.startsWith('denied') ? 'text-rose-300 w-40' : 'text-white/80 w-40'}>{EVENT_LABELS[l.event] || l.event}</span>
                            <span className="font-mono text-white/35">viewer {l.viewer?.slice(0, 6)}</span>
                            <span className="text-white/30 truncate max-w-xs">{l.user_agent}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
