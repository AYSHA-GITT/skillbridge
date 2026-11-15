import React, { useCallback, useEffect, useState } from 'react';
import { TbCheck, TbX, TbDownload, TbRefresh } from 'react-icons/tb';
import passportService from '../services/passportService';
import AlertBanner from './AlertBanner';
import { KIND_LABELS, ReviewBadge, SafeLink, fmtDateTime, displaySkill } from './PassportBits';

const FILTERS = ['pending', 'verified', 'rejected'];

/** Admin queue for Skill Passport evidence submitted for verification. */
export default function AdminEvidenceReview() {
  const [status, setStatus] = useState('pending');
  const [items, setItems] = useState([]);
  const [notes, setNotes] = useState({});
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems((await passportService.adminListEvidence(status)).evidence);
    } catch {
      setAlert({ type: 'error', message: 'Could not load the evidence queue.' });
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (id, decision) => {
    try {
      await passportService.adminReviewEvidence(id, decision, notes[id] || '');
      setAlert({ type: 'success', message: `Evidence ${decision}.` });
      load();
    } catch (e) {
      setAlert({ type: 'error', message: e?.response?.data?.error || 'Review failed.' });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="font-heading text-xl font-bold text-white">Skill Passport evidence review</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Accept evidence only after checking the link or file. Accepting marks the linked skills as verified on the
            student's passport; the decision is reset automatically if the student edits the evidence.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {FILTERS.map((f) => (
            <button key={f} onClick={() => setStatus(f)}
              className={`text-xs px-3 py-1.5 rounded-lg border capitalize ${status === f ? 'border-teal-400 text-teal-300' : 'border-slate-700 text-slate-400'}`}>
              {f}
            </button>
          ))}
          <button onClick={load} className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:text-white" title="Refresh">
            <TbRefresh className="w-4 h-4" />
          </button>
        </div>
      </div>

      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-500">No {status} evidence.</p>
      ) : (
        <div className="space-y-3">
          {items.map((e) => (
            <div key={e.id} className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs">
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-white">
                    {KIND_LABELS[e.kind]}: {e.title}
                    {e.organization && <span className="text-slate-400 font-normal"> — {e.organization}</span>}
                  </div>
                  <div className="text-slate-400">
                    {e.student?.name} {e.student?.college && `· ${e.student.college}`} · requested {fmtDateTime(e.review_requested_at)}
                  </div>
                </div>
                <ReviewBadge status={e.review_status} />
              </div>
              {e.description && <p className="text-slate-300 whitespace-pre-line">{e.description}</p>}
              {e.url && <SafeLink href={e.url} className="text-teal-300">{e.url}</SafeLink>}
              <div className="flex flex-wrap gap-1">
                <span className="text-slate-500">Claims:</span>
                {e.skills.map((s) => <span key={s.id} className="px-2 py-0.5 rounded-full bg-white/5 text-slate-300">{displaySkill(s.skill_name)}</span>)}
              </div>
              {e.has_file && (
                <button onClick={() => passportService.adminDownloadEvidenceFile(e.id, e.original_filename)}
                  className="flex items-center gap-1 text-slate-300 hover:text-white">
                  <TbDownload className="w-3.5 h-3.5" /> {e.original_filename || 'Attached file'}
                </button>
              )}
              {e.review_note && <p className="text-slate-400">Note: {e.review_note}</p>}
              {status === 'pending' && (
                <div className="flex flex-col sm:flex-row gap-2 pt-1">
                  <input className="input-field text-xs py-2" maxLength={500} placeholder="Note to the student (required when rejecting)"
                    value={notes[e.id] || ''} onChange={(ev) => setNotes({ ...notes, [e.id]: ev.target.value })} />
                  <button onClick={() => decide(e.id, 'verified')}
                    className="px-3 py-2 rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 flex items-center gap-1 whitespace-nowrap">
                    <TbCheck className="w-4 h-4" /> Accept
                  </button>
                  <button onClick={() => decide(e.id, 'rejected')}
                    className="px-3 py-2 rounded-lg bg-rose-500/15 border border-rose-500/40 text-rose-300 flex items-center gap-1 whitespace-nowrap">
                    <TbX className="w-4 h-4" /> Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
