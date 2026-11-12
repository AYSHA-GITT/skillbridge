import React, { useCallback, useEffect, useState } from 'react';
import { TbRefresh, TbBriefcase, TbClock, TbAlertTriangle, TbCpu } from 'react-icons/tb';
import skillService from '../services/skillService';
import AlertBanner from './AlertBanner';

const STATUS_CLS = {
  success: 'text-emerald-300',
  ok: 'text-emerald-300',
  partial: 'text-amber-300',
  degraded: 'text-amber-300',
  running: 'text-cyan-300',
  skipped: 'text-slate-400',
  not_configured: 'text-slate-500',
  failed: 'text-rose-300',
  error: 'text-rose-300',
  auth_failed: 'text-rose-300',
  rate_limited: 'text-amber-300'
};

const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : '—');

function Card({ label, value, hint, cls = 'text-white' }) {
  return (
    <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
      <div className="text-[11px] text-slate-400">{label}</div>
      <div className={`font-heading text-2xl font-bold ${cls}`}>{value ?? 0}</div>
      {hint && <div className="text-[10px] text-slate-500 mt-0.5">{hint}</div>}
    </div>
  );
}

/** Admin view of the two-hour job synchronization, provider health, AI services and model metrics. */
export default function AdminJobSync() {
  const [data, setData] = useState(null);
  const [health, setHealth] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [alert, setAlert] = useState(null);

  const load = useCallback(async () => {
    try {
      const [ov, h] = await Promise.all([
        skillService.getAdminJobsOverview(),
        skillService.getAdminSystemHealth().catch(() => null)
      ]);
      setData(ov);
      setHealth(h);
    } catch {
      setAlert({ type: 'error', message: 'Could not load job synchronization status.' });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const syncNow = async () => {
    setSyncing(true);
    try {
      const res = await skillService.adminSyncJobs();
      const r = res.run || {};
      setAlert({
        type: r.status === 'success' ? 'success' : r.status === 'failed' ? 'error' : 'warning',
        message: `Run #${r.id} ${r.status}: ${r.inserted_count} new, ${r.updated_count} updated, ` +
          `${r.expired_count} expired, ${r.invalid_count} rejected.${r.error ? ` ${r.error}` : ''}`
      });
    } catch (err) {
      setAlert({
        type: err.response?.status === 409 ? 'warning' : 'error',
        message: err.response?.status === 409
          ? 'A synchronization is already running; the manual run was skipped (no duplicates created).'
          : (err.response?.data?.error || 'Manual synchronization failed.')
      });
    } finally {
      setSyncing(false);
      load();
    }
  };

  if (!data) {
    return <div className="text-xs text-slate-400 font-mono">Loading job synchronization status...</div>;
  }

  const t = data.totals || {};
  const s = data.schedule || {};
  const salary = health?.models?.salary;

  return (
    <div className="space-y-6">
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="font-heading text-xl font-bold text-white flex items-center gap-2">
            <TbBriefcase className="w-5 h-5 text-cyan-300" /> Job Synchronization
          </h2>
          <p className="text-xs text-slate-400 flex items-center gap-1 mt-1">
            <TbClock className="w-3.5 h-3.5" />
            Every {s.interval_hours ?? 2} h · last success {fmt(s.last_successful_sync)} · next {fmt(s.next_scheduled_sync)}
            {s.currently_running?.running && ' · a run is in progress'}
          </p>
        </div>
        <button
          onClick={syncNow}
          disabled={syncing}
          className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center gap-2 disabled:opacity-50"
        >
          <TbRefresh className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Synchronizing...' : 'Sync now'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card label="Total jobs stored" value={t.jobs_total} />
        <Card label="New in last 24 h" value={t.new_jobs_last_24h} cls="text-cyan-300" />
        <Card label="Active" value={t.jobs_by_status?.active} cls="text-emerald-300"
          hint={`${t.jobs_by_status?.stale || 0} not re-confirmed recently`} />
        <Card label="Expired / archived" value={t.jobs_by_status?.expired} cls="text-rose-300"
          hint={`${t.jobs_by_status?.sample || 0} demo listings (hidden)`} />
        <Card label="Duplicates flagged" value={t.duplicates_flagged} hint="hidden from search" />
        <Card label="Jobs without skills" value={t.jobs_without_skills} hint="match score shown as n/a" />
        <Card label="Failed runs (24 h)" value={s.failed_runs_last_24h} cls={s.failed_runs_last_24h ? 'text-rose-300' : 'text-white'} />
        <Card label="Alert matches (24 h)" value={data.activity?.alert_matches_last_24h}
          hint={`${data.activity?.applications_total || 0} tracked applications`} />
      </div>

      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
        <h3 className="text-sm font-semibold text-white">Provider health</h3>
        <table className="w-full text-xs">
          <thead className="text-slate-400 text-left">
            <tr><th className="py-1">Provider</th><th>Configured</th><th>Last result</th><th>Last success</th><th>Requests / run</th></tr>
          </thead>
          <tbody>
            {(data.providers || []).map((p) => (
              <tr key={p.provider} className="border-t border-slate-800">
                <td className="py-1.5 text-white">{p.source}</td>
                <td className={p.configured ? 'text-emerald-300' : 'text-slate-500'}>{p.configured ? 'Yes' : 'No (credentials missing)'}</td>
                <td className={STATUS_CLS[p.last_result?.status] || 'text-slate-400'}>
                  {p.last_result ? `${p.last_result.status} · ${p.last_result.accepted ?? 0} accepted` : '—'}
                  {p.last_result?.errors?.length > 0 && (
                    <span title={p.last_result.errors.join('\n')}> <TbAlertTriangle className="inline w-3.5 h-3.5" /></span>
                  )}
                </td>
                <td className="text-slate-300">{fmt(p.last_success_at)}</td>
                <td className="text-slate-300">{p.max_requests_per_run}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="text-[11px] text-slate-500">
          By status: {(data.by_provider || []).map((b) => `${b.provider}/${b.status}: ${b.count}`).join(' · ')}
        </div>
      </div>

      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
        <h3 className="text-sm font-semibold text-white">Recent synchronization runs</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="text-slate-400 text-left">
              <tr><th className="py-1">#</th><th>Trigger</th><th>Started</th><th>Status</th><th>Fetched</th><th>New</th><th>Updated</th><th>Dupes</th><th>Rejected</th><th>Expired</th><th>Error</th></tr>
            </thead>
            <tbody>
              {(data.recent_runs || []).map((r) => (
                <tr key={r.id} className="border-t border-slate-800 text-slate-300">
                  <td className="py-1.5">{r.id}</td>
                  <td>{r.trigger}</td>
                  <td>{fmt(r.started_at)}</td>
                  <td className={STATUS_CLS[r.status]}>{r.status}</td>
                  <td>{r.fetched_count}</td>
                  <td>{r.inserted_count}</td>
                  <td>{r.updated_count}</td>
                  <td>{r.duplicate_count}</td>
                  <td>{r.invalid_count}</td>
                  <td>{r.expired_count}</td>
                  <td className="text-rose-300 max-w-xs truncate" title={r.error || ''}>{r.error || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs">
            <h3 className="text-sm font-semibold text-white flex items-center gap-1.5"><TbCpu className="w-4 h-4" /> AI services</h3>
            {(Array.isArray(health.ai_services) ? health.ai_services : []).map((p) => (
              <div key={p.key || p.name} className="flex justify-between">
                <span className="text-slate-300">{p.name || p.key}</span>
                <span className={p.is_available ? 'text-emerald-300' : 'text-slate-500'}>
                  {p.is_available ? `available (${p.model})` : 'not configured / unreachable'}
                  {p.is_active ? ' · active' : ''}
                </span>
              </div>
            ))}
          </div>
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs">
            <h3 className="text-sm font-semibold text-white">Salary model evaluation</h3>
            {salary?.cv_results ? (
              <>
                <table className="w-full">
                  <thead className="text-slate-400 text-left"><tr><th>Model</th><th>MAE (LPA)</th><th>RMSE</th><th>R²</th></tr></thead>
                  <tbody>
                    {Object.entries(salary.cv_results).map(([name, m]) => (
                      <tr key={name} className="border-t border-slate-800 text-slate-300">
                        <td className="py-1">{name}</td><td>{m.mae_lpa}</td><td>{m.rmse_lpa}</td><td>{m.r2}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="text-[10px] text-amber-300/80">{salary.caveat}</p>
              </>
            ) : <p className="text-slate-500">Unavailable</p>}
          </div>
        </div>
      )}
    </div>
  );
}
