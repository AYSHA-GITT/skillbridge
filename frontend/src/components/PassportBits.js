import React from 'react';
import {
  TbRosetteDiscountCheck,
  TbClipboardCheck,
  TbHourglass,
  TbPaperclip,
  TbSparkles,
  TbUser
} from 'react-icons/tb';

/** Visual language shared by the owner passport page and the public recruiter view. */
export const STATUS_STYLES = {
  verified: { cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40', icon: TbRosetteDiscountCheck },
  assessment_completed: { cls: 'bg-sky-500/15 text-sky-300 border-sky-500/40', icon: TbClipboardCheck },
  pending_verification: { cls: 'bg-amber-500/15 text-amber-300 border-amber-500/40', icon: TbHourglass },
  evidence_submitted: { cls: 'bg-violet-500/15 text-violet-300 border-violet-500/40', icon: TbPaperclip },
  ai_extracted: { cls: 'bg-slate-500/15 text-slate-300 border-slate-500/40', icon: TbSparkles },
  self_declared: { cls: 'bg-white/5 text-white/60 border-white/15', icon: TbUser }
};

export const STATUS_ORDER = [
  'verified',
  'assessment_completed',
  'pending_verification',
  'evidence_submitted',
  'ai_extracted',
  'self_declared'
];

export const FALLBACK_STATUS_LABELS = {
  verified: 'Verified',
  assessment_completed: 'Assessment completed',
  pending_verification: 'Pending verification',
  evidence_submitted: 'Evidence submitted',
  ai_extracted: 'AI-extracted',
  self_declared: 'Self-declared'
};

export const KIND_LABELS = {
  project: 'Project',
  certificate: 'Certificate',
  experience: 'Experience',
  practical_challenge: 'Practical challenge'
};

export const REVIEW_LABELS = {
  not_requested: 'Not reviewed',
  pending: 'Pending review',
  verified: 'Reviewed & accepted',
  rejected: 'Rejected'
};

export const REVIEW_CLS = {
  not_requested: 'text-white/50 border-white/15',
  pending: 'text-amber-300 border-amber-500/40',
  verified: 'text-emerald-300 border-emerald-500/40',
  rejected: 'text-rose-300 border-rose-500/40'
};

export const SECTION_LABELS = {
  profile: 'Professional profile',
  links: 'Profile links',
  education: 'Education',
  skills: 'Skills',
  projects: 'Projects',
  certifications: 'Certifications',
  experience: 'Experience',
  practical_challenges: 'Practical challenges',
  assessments: 'Assessment results',
  career_interests: 'Career interests'
};

export const GROUP_ORDER = ['languages_frameworks', 'ai_ml_data', 'technical', 'soft_skills'];

// Skills are stored lower-case; show acronyms and well-known names the way people write them.
const SKILL_DISPLAY = {
  sql: 'SQL', aws: 'AWS', gcp: 'GCP', html: 'HTML', css: 'CSS', nlp: 'NLP', 'ci/cd': 'CI/CD', php: 'PHP',
  'rest api': 'REST API', graphql: 'GraphQL', nosql: 'NoSQL', mysql: 'MySQL', postgresql: 'PostgreSQL',
  mongodb: 'MongoDB', sqlite: 'SQLite', javascript: 'JavaScript', typescript: 'TypeScript', 'node.js': 'Node.js',
  'next.js': 'Next.js', 'c++': 'C++', 'c#': 'C#', '.net': '.NET', 'scikit-learn': 'scikit-learn', pytorch: 'PyTorch',
  tensorflow: 'TensorFlow', fastapi: 'FastAPI', github: 'GitHub', gitlab: 'GitLab', 'power bi': 'Power BI',
  'generative ai': 'Generative AI', 'tailwind css': 'Tailwind CSS', matlab: 'MATLAB', ios: 'iOS', dsa: 'DSA',
  'machine learning': 'Machine Learning', 'deep learning': 'Deep Learning', 'computer vision': 'Computer Vision',
  devops: 'DevOps', opencv: 'OpenCV', numpy: 'NumPy', 'ci cd': 'CI/CD', llm: 'LLM', api: 'API', ui: 'UI', ux: 'UX'
};
export const displaySkill = (name = '') =>
  SKILL_DISPLAY[name.toLowerCase()] || name.replace(/(^|[\s-])([a-z])/g, (m, p, c) => p + c.toUpperCase());

export const fmtDate =(iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—');
export const fmtDateTime = (iso) => (iso ? new Date(iso).toLocaleString() : '—');

export function StatusBadge({ status, label, title }) {
  const st = STATUS_STYLES[status] || STATUS_STYLES.self_declared;
  const Icon = st.icon;
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border whitespace-nowrap ${st.cls}`}
    >
      <Icon className="w-3 h-3" />
      {label || FALLBACK_STATUS_LABELS[status] || status}
    </span>
  );
}

export function ReviewBadge({ status }) {
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border whitespace-nowrap ${REVIEW_CLS[status] || REVIEW_CLS.not_requested}`}>
      {REVIEW_LABELS[status] || status}
    </span>
  );
}

/** Explains the six verification states, so nobody mistakes a resume mention for verification. */
export function StatusLegend({ labels = FALLBACK_STATUS_LABELS, descriptions = {} }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
      {STATUS_ORDER.map((s) => (
        <div key={s} className="flex items-start gap-2 text-[11px] text-white/55">
          <StatusBadge status={s} label={labels[s]} />
          <span className="leading-snug">{descriptions[s]}</span>
        </div>
      ))}
    </div>
  );
}

/** Only http(s) links are rendered as anchors (the API also rejects anything else). */
export function SafeLink({ href, children, className = '' }) {
  if (!href || !/^https?:\/\//i.test(href)) return <span className={className}>{children}</span>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={`${className} hover:underline break-all`}>
      {children}
    </a>
  );
}
