import React, { useCallback, useEffect, useState } from 'react';
import { TbX, TbBell, TbTrash, TbPlus, TbSettings } from 'react-icons/tb';
import skillService from '../services/skillService';

const splitList = (text) =>
  text.split(',').map((s) => s.trim()).filter(Boolean);

const FREQUENCIES = [
  { value: 'instant', label: 'Every refresh (up to 12×/day)' },
  { value: 'daily', label: 'Daily digest' },
  { value: 'weekly', label: 'Weekly digest' }
];

const emptyAlert = { name: '', roles: '', locations: '', skills: '', frequency: 'daily', min_match_score: 50 };

/**
 * Job preferences (used to score location / experience fit) and in-app job alerts.
 * Alerts are evaluated by the backend after each two-hour sync; a job is never alerted twice.
 */
export default function JobAlertsPanel({ onClose, onOpenJob }) {
  const [tab, setTab] = useState('notifications');
  const [prefs, setPrefs] = useState(null);
  const [prefsForm, setPrefsForm] = useState({ roles: '', locations: '', modes: [], years: 0, relocate: false });
  const [alerts, setAlerts] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [newAlert, setNewAlert] = useState(emptyAlert);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [p, a, n] = await Promise.all([
        skillService.getJobPreferences(),
        skillService.getJobAlerts(),
        skillService.getJobAlertNotifications()
      ]);
      const pr = p.preferences || {};
      setPrefs(pr);
      setPrefsForm({
        roles: (pr.preferred_roles || []).join(', '),
        locations: (pr.preferred_locations || []).join(', '),
        modes: pr.work_modes || [],
        years: pr.experience_years || 0,
        relocate: !!pr.open_to_relocation
      });
      setAlerts(a.alerts || []);
      setNotifications(n.notifications || []);
    } catch {
      setMessage({ type: 'error', text: 'Could not load your job alerts.' });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const savePrefs = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await skillService.saveJobPreferences({
        preferred_roles: splitList(prefsForm.roles),
        preferred_locations: splitList(prefsForm.locations),
        work_modes: prefsForm.modes,
        experience_years: Number(prefsForm.years) || 0,
        open_to_relocation: prefsForm.relocate
      });
      setMessage({ type: 'success', text: 'Preferences saved. Match scores now consider location and experience.' });
      load();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.error || 'Could not save preferences.' });
    } finally {
      setBusy(false);
    }
  };

  const createAlert = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await skillService.createJobAlert({
        name: newAlert.name || splitList(newAlert.roles)[0] || 'My alert',
        roles: splitList(newAlert.roles),
        locations: splitList(newAlert.locations),
        skills: splitList(newAlert.skills),
        frequency: newAlert.frequency,
        min_match_score: Number(newAlert.min_match_score)
      });
      setNewAlert(emptyAlert);
      setMessage({ type: 'success', text: 'Alert created. It is checked after every two-hour refresh.' });
      load();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.error || 'Could not create alert.' });
    } finally {
      setBusy(false);
    }
  };

  const toggleAlert = async (alert) => {
    await skillService.updateJobAlert(alert.id, { is_active: !alert.is_active });
    load();
  };

  const deleteAlert = async (alert) => {
    await skillService.deleteJobAlert(alert.id);
    load();
  };

  const markAllRead = async () => {
    await skillService.markJobAlertNotificationsRead();
    load();
  };

  const input = 'input-field text-xs py-2 w-full bg-base-950/80 border-base-700/80 rounded-xl';

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="surface max-w-2xl w-full rounded-3xl border border-accent-400/30 p-6 max-h-[90vh] overflow-y-auto space-y-4 animate-scale-in">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="font-heading text-lg font-bold text-white flex items-center gap-2">
              <TbBell className="w-5 h-5 text-accent-300" /> Job Alerts & Preferences
            </h2>
            <p className="text-[11px] text-white/50">
              Alerts are shown here in SkillBridge (no emails are sent). Each job is alerted at most once.
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10">
            <TbX className="w-4 h-4" />
          </button>
        </div>

        <div className="flex gap-1 bg-base-950 p-0.5 rounded-xl border border-base-800 w-fit text-[11px]">
          {[['notifications', `New matches (${notifications.filter((n) => !n.is_read).length})`],
            ['alerts', `My alerts (${alerts.length})`], ['preferences', 'Preferences']].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-3 py-1 rounded-lg font-medium ${tab === key ? 'bg-accent-500/20 text-accent-300' : 'text-white/50 hover:text-white'}`}
            >
              {label}
            </button>
          ))}
        </div>

        {message && (
          <p className={`text-xs ${message.type === 'error' ? 'text-rose-300' : 'text-emerald-300'}`}>{message.text}</p>
        )}

        {tab === 'notifications' && (
          <div className="space-y-2">
            {notifications.length === 0 ? (
              <p className="text-xs text-white/50">
                No alert matches yet. Create an alert — new jobs are checked after every refresh.
              </p>
            ) : (
              <>
                <button onClick={markAllRead} className="btn-ghost text-[11px] py-1 px-2.5">Mark all as read</button>
                {notifications.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => n.job && onOpenJob(n.job)}
                    className={`w-full text-left p-3 rounded-xl border text-xs ${n.is_read ? 'border-base-800 bg-base-950/40' : 'border-accent-400/40 bg-accent-500/5'}`}
                  >
                    <div className="flex justify-between gap-2">
                      <span className="text-white font-medium">{n.job?.title}</span>
                      <span className="font-mono text-accent-300">{n.match_score}% fit</span>
                    </div>
                    <div className="text-white/50">{n.job?.company} · {n.job?.location} · {n.job?.freshness?.posted_label}</div>
                  </button>
                ))}
              </>
            )}
          </div>
        )}

        {tab === 'alerts' && (
          <div className="space-y-4">
            <div className="space-y-2">
              {alerts.map((a) => (
                <div key={a.id} className="flex items-center justify-between p-3 rounded-xl border border-base-800 bg-base-950/50 text-xs">
                  <div>
                    <div className="text-white font-medium">{a.name}</div>
                    <div className="text-white/50">
                      {[a.roles.join(', '), a.locations.join(', '), a.skills.join(', ')].filter(Boolean).join(' · ')}
                    </div>
                    <div className="text-white/40">
                      {FREQUENCIES.find((f) => f.value === a.frequency)?.label} · min fit {a.min_match_score}%
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => toggleAlert(a)} className="btn-ghost text-[11px] py-1 px-2">
                      {a.is_active ? 'Pause' : 'Resume'}
                    </button>
                    <button onClick={() => deleteAlert(a)} className="p-1.5 text-white/40 hover:text-rose-400" title="Delete alert">
                      <TbTrash className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <form onSubmit={createAlert} className="space-y-2 border-t border-base-800 pt-3 text-xs">
              <h4 className="font-semibold text-white/80 flex items-center gap-1"><TbPlus className="w-4 h-4" /> New alert</h4>
              <input className={input} placeholder="Alert name (optional)" value={newAlert.name}
                onChange={(e) => setNewAlert({ ...newAlert, name: e.target.value })} />
              <input className={input} placeholder="Roles, comma separated (e.g. data analyst, python developer)"
                value={newAlert.roles} onChange={(e) => setNewAlert({ ...newAlert, roles: e.target.value })} />
              <input className={input} placeholder="Locations (e.g. Bengaluru, Mangaluru, remote)"
                value={newAlert.locations} onChange={(e) => setNewAlert({ ...newAlert, locations: e.target.value })} />
              <input className={input} placeholder="Skills the job should mention (optional)"
                value={newAlert.skills} onChange={(e) => setNewAlert({ ...newAlert, skills: e.target.value })} />
              <div className="grid grid-cols-2 gap-2">
                <select className={input} value={newAlert.frequency}
                  onChange={(e) => setNewAlert({ ...newAlert, frequency: e.target.value })}>
                  {FREQUENCIES.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                </select>
                <label className="flex items-center gap-2 text-white/60">
                  Min fit
                  <input type="number" min="0" max="100" className={input} value={newAlert.min_match_score}
                    onChange={(e) => setNewAlert({ ...newAlert, min_match_score: e.target.value })} />
                </label>
              </div>
              <button type="submit" disabled={busy} className="btn-primary text-xs py-2 px-4">Create alert</button>
            </form>
          </div>
        )}

        {tab === 'preferences' && prefs && (
          <form onSubmit={savePrefs} className="space-y-2 text-xs">
            <p className="text-white/50 flex items-center gap-1">
              <TbSettings className="w-4 h-4" /> Used to score location, work-mode and experience fit, and to discover jobs for your target roles.
            </p>
            <input className={input} placeholder="Preferred roles (comma separated)" value={prefsForm.roles}
              onChange={(e) => setPrefsForm({ ...prefsForm, roles: e.target.value })} />
            <input className={input} placeholder="Preferred locations (e.g. Bengaluru, Mangaluru, Bhatkal)"
              value={prefsForm.locations} onChange={(e) => setPrefsForm({ ...prefsForm, locations: e.target.value })} />
            <div className="flex items-center gap-3 text-white/70">
              {['Remote', 'Hybrid', 'Onsite'].map((m) => (
                <label key={m} className="flex items-center gap-1">
                  <input type="checkbox" checked={prefsForm.modes.includes(m)}
                    onChange={(e) => setPrefsForm({
                      ...prefsForm,
                      modes: e.target.checked ? [...prefsForm.modes, m] : prefsForm.modes.filter((x) => x !== m)
                    })} />
                  {m}
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2 text-white/70">
              Professional experience (years)
              <input type="number" min="0" max="50" step="0.5" className={`${input} w-24`} value={prefsForm.years}
                onChange={(e) => setPrefsForm({ ...prefsForm, years: e.target.value })} />
            </label>
            <label className="flex items-center gap-2 text-white/70">
              <input type="checkbox" checked={prefsForm.relocate}
                onChange={(e) => setPrefsForm({ ...prefsForm, relocate: e.target.checked })} />
              Open to relocation
            </label>
            <button type="submit" disabled={busy} className="btn-primary text-xs py-2 px-4">Save preferences</button>
          </form>
        )}
      </div>
    </div>
  );
}
