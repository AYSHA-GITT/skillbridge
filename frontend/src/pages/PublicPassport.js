import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import passportService from '../services/passportService';
import {
  StatusBadge,
  ReviewBadge,
  StatusLegend,
  SafeLink,
  GROUP_ORDER,
  KIND_LABELS,
  fmtDate,
  displaySkill
} from '../components/PassportBits';
import {
  TbId,
  TbSchool,
  TbBrandLinkedin,
  TbBrandGithub,
  TbWorld,
  TbFileTypePdf,
  TbTarget,
  TbClipboardCheck,
  TbLock
} from 'react-icons/tb';

const SECTION_TITLES = {
  projects: 'Projects',
  certifications: 'Certifications',
  experience: 'Experience',
  practical_challenges: 'Practical challenges'
};

function Section({ title, icon: Icon, children }) {
  return (
    <section className="glass p-5 rounded-2xl space-y-3">
      <h2 className="font-heading text-sm font-bold text-white flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 text-accent-400" />}
        {title}
      </h2>
      {children}
    </section>
  );
}

/** Recruiter-facing view of a shared Skill Passport. No login; access is controlled by the link. */
export default function PublicPassport() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Keep the secret link out of Referer headers sent to linked sites
    const meta = document.createElement('meta');
    meta.name = 'referrer';
    meta.content = 'no-referrer';
    document.head.appendChild(meta);
    document.title = 'Skill Passport · SkillBridge';
    passportService
      .getPublicPassport(token)
      .then(setData)
      .catch((e) => setError(e?.response?.data?.error || 'This Skill Passport could not be loaded.'));
    return () => {
      document.head.removeChild(meta);
    };
  }, [token]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="glass p-8 rounded-2xl max-w-md text-center space-y-3">
          <TbLock className="w-10 h-10 text-white/30 mx-auto" />
          <h1 className="font-heading text-lg font-bold text-white">Skill Passport unavailable</h1>
          <p className="text-sm text-white/55">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return <div className="min-h-screen flex items-center justify-center text-white/40 text-sm font-mono">Loading Skill Passport…</div>;
  }

  const has = (k) => data.sections.includes(k);
  const skills = data.skills || [];
  const verifiedCount = skills.filter((s) => s.status === 'verified').length;
  const links = data.links || {};

  return (
    <div className="min-h-screen">
      <header className="border-b border-base-700/60 bg-base-900/60">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <span className="font-heading font-bold text-white flex items-center gap-2">
            <TbId className="w-5 h-5 text-accent-400" /> SkillBridge <span className="text-white/40 font-normal">Skill Passport</span>
          </span>
          {data.link?.allow_pdf && (
            <a href={passportService.publicPdfUrl(token)} rel="noopener noreferrer"
              className="btn-ghost text-xs flex items-center gap-1.5">
              <TbFileTypePdf className="w-4 h-4" /> Download PDF
            </a>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-5">
        <div className="glass p-6 rounded-2xl flex flex-col md:flex-row gap-5 md:items-center">
          <div className="w-16 h-16 rounded-2xl bg-accent-500/15 border border-accent-400/30 flex items-center justify-center font-heading text-2xl font-bold text-accent-300 flex-shrink-0">
            {(data.name || '?').slice(0, 1).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0 space-y-1">
            <h1 className="font-heading text-2xl font-bold text-white">{data.name}</h1>
            {data.profile?.headline && <p className="text-accent-300 text-sm">{data.profile.headline}</p>}
            {has('education') && data.education?.current && (data.education.current.program || data.education.current.institution) && (
              <p className="text-xs text-white/55 flex items-center gap-1.5">
                <TbSchool className="w-3.5 h-3.5" />
                {[data.education.current.program, data.education.current.institution, data.education.current.year].filter(Boolean).join(' · ')}
              </p>
            )}
            <div className="flex flex-wrap gap-3 text-xs pt-1">
              {links.linkedin_url && <SafeLink href={links.linkedin_url} className="text-sky-300 flex items-center gap-1"><TbBrandLinkedin className="w-4 h-4" />LinkedIn</SafeLink>}
              {links.github_url && <SafeLink href={links.github_url} className="text-white/70 flex items-center gap-1"><TbBrandGithub className="w-4 h-4" />GitHub</SafeLink>}
              {links.portfolio_url && <SafeLink href={links.portfolio_url} className="text-accent-300 flex items-center gap-1"><TbWorld className="w-4 h-4" />Portfolio</SafeLink>}
            </div>
          </div>
          {has('skills') && (
            <div className="surface p-4 text-center md:w-40">
              <div className="font-heading text-3xl font-bold text-emerald-300">{verifiedCount}</div>
              <div className="text-[11px] text-white/50">verified of {skills.length} skill{skills.length === 1 ? '' : 's'} shown</div>
            </div>
          )}
        </div>

        {data.profile?.summary && (
          <Section title="Professional profile" icon={TbId}>
            <p className="text-sm text-white/70 whitespace-pre-line leading-relaxed">{data.profile.summary}</p>
          </Section>
        )}

        {has('skills') && (
          <Section title="Skills" icon={TbClipboardCheck}>
            {data.skill_filter !== 'all' && (
              <p className="text-[11px] text-white/40">
                The student chose to show {data.skill_filter === 'verified' ? 'only verified skills' : 'only skills with evidence or an assessment'}.
              </p>
            )}
            {skills.length === 0 && <p className="text-xs text-white/40 italic">No skills to show.</p>}
            {GROUP_ORDER.map((g) => {
              const rows = skills.filter((s) => s.group === g);
              if (!rows.length) return null;
              return (
                <div key={g} className="space-y-1.5">
                  <h3 className="text-[11px] uppercase tracking-wider text-white/40 font-semibold pt-2">{data.skill_groups[g]}</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-white/35">
                          <th className="py-1.5 pr-3 font-medium">Skill</th>
                          <th className="py-1.5 pr-3 font-medium">Status</th>
                          <th className="py-1.5 pr-3 font-medium">Proficiency</th>
                          <th className="py-1.5 pr-3 font-medium">Assessment</th>
                          <th className="py-1.5 pr-3 font-medium">Evidence</th>
                          <th className="py-1.5 font-medium">Last verified</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-base-700/60">
                        {rows.map((s) => (
                          <tr key={s.skill_name} className="align-top">
                            <td className="py-2 pr-3 text-white font-semibold">{displaySkill(s.skill_name)}</td>
                            <td className="py-2 pr-3"><StatusBadge status={s.status} label={s.status_label} title={data.status_descriptions[s.status]} /></td>
                            <td className="py-2 pr-3 text-white/70">{s.proficiency}</td>
                            <td className="py-2 pr-3 text-white/70">
                              {s.assessment ? `${Math.round(s.assessment.score_percent)}% (${s.assessment.correct}/${s.assessment.total})` : '—'}
                            </td>
                            <td className="py-2 pr-3 text-white/60 space-y-0.5">
                              {s.resume_evidence && <div>Resume ({String(s.resume_evidence.evidence_strength).replace('_', ' ')})</div>}
                              {s.evidence.map((e, i) => (
                                <div key={i}>{KIND_LABELS[e.kind]}: {e.title}</div>
                              ))}
                              {!s.resume_evidence && s.evidence.length === 0 && '—'}
                            </td>
                            <td className="py-2 text-white/60 whitespace-nowrap">{fmtDate(s.last_verified_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </Section>
        )}

        {Object.entries(SECTION_TITLES).map(([key, title]) =>
          has(key) ? (
            <Section key={key} title={title}>
              {(data[key] || []).length === 0 ? (
                <p className="text-xs text-white/40 italic">None added.</p>
              ) : (
                <div className="space-y-3">
                  {data[key].map((e, i) => (
                    <div key={i} className="surface p-4 space-y-1.5">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                        <div>
                          <div className="text-sm font-semibold text-white">{e.title}</div>
                          <div className="text-xs text-white/50">
                            {[e.organization, [e.start_date, e.end_date].filter(Boolean).join(' – ')].filter(Boolean).join(' · ')}
                          </div>
                        </div>
                        <ReviewBadge status={e.review_status} />
                      </div>
                      {e.description && <p className="text-xs text-white/60 whitespace-pre-line">{e.description}</p>}
                      {e.url && <SafeLink href={e.url} className="text-xs text-accent-300">{e.url}</SafeLink>}
                      {e.skills.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {e.skills.map((s) => <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-white/60">{displaySkill(s)}</span>)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Section>
          ) : null
        )}

        {has('career_interests') && data.career_interests && (
          <Section title="Career interests" icon={TbTarget}>
            <dl className="text-xs grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                ['Target career', data.career_interests.target_career],
                ['Preferred roles', data.career_interests.preferred_roles?.join(', ')],
                ['Locations', data.career_interests.preferred_locations?.join(', ')],
                ['Work modes', data.career_interests.work_modes?.join(', ')],
                ['Job types', data.career_interests.job_types?.join(', ')]
              ].filter(([, v]) => v).map(([k, v]) => (
                <div key={k} className="flex gap-2"><dt className="text-white/40 w-28 flex-shrink-0">{k}</dt><dd className="text-white/80">{v}</dd></div>
              ))}
            </dl>
          </Section>
        )}

        <Section title="How to read this passport">
          <StatusLegend labels={data.status_labels} descriptions={data.status_descriptions} />
          <p className="text-[11px] text-white/40">
            "Verified" means the student passed a SkillBridge assessment (pass mark {data.pass_threshold}%) or a reviewer accepted the linked evidence.
            Resume mentions and submitted evidence alone are never treated as verification. Generated {fmtDate(data.generated_at)}
            {data.link?.expires_at && ` · this link expires ${fmtDate(data.link.expires_at)}`}.
          </p>
        </Section>
      </main>
    </div>
  );
}
