import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NextSteps from './NextSteps';
import AddToRoadmapButton from './AddToRoadmapButton';
import skillService from '../services/skillService';
import recruiterService from '../services/recruiterService';
import { VerificationRequestItem } from '../pages/EmployerAccess';
import { VerificationRequestsPanel } from '../pages/recruiter/RecruiterCandidateProfile';
import { readinessSteps } from '../pages/Readiness';
import { SkillGroupActions, categoryLabel } from '../pages/Roadmap';
import { AttemptNextStep } from '../pages/Assessment';
import { careerJobsLink } from '../pages/Company';

jest.mock('../services/api', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() }
}));
jest.mock('../services/skillService', () => ({
  __esModule: true,
  default: { addSkillToRoadmap: jest.fn() }
}));
jest.mock('../services/recruiterService', () => ({
  __esModule: true,
  default: { requestSkillVerification: jest.fn(), cancelVerificationRequest: jest.fn() },
  candidateService: {},
  errorText: (e, f) => e?.response?.data?.error || f
}));

const inRouter = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);
const hrefOf = (text) => screen.getByText(text).closest('a').getAttribute('href');

beforeEach(() => jest.clearAllMocks());

describe('NextSteps', () => {
  test('renders each step as a link and skips falsy entries', () => {
    inRouter(<NextSteps steps={[{ to: '/assessment', label: 'Verify skills', detail: 'Pass mark 70%' }, false, null]} />);
    expect(hrefOf('Verify skills')).toBe('/assessment');
    expect(screen.getByText('Pass mark 70%')).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(1);
  });

  test('renders nothing without steps', () => {
    const { container } = inRouter(<NextSteps steps={[false]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('AddToRoadmapButton', () => {
  test('adds a skill once and then links to the roadmap', async () => {
    skillService.addSkillToRoadmap.mockResolvedValue({ added: true, on_roadmap: true, message: 'kafka was added' });
    inRouter(<AddToRoadmapButton skill="kafka" jobId={7} />);
    fireEvent.click(screen.getByText('Add to roadmap'));
    expect(await screen.findByText('On your roadmap')).toBeInTheDocument();
    expect(skillService.addSkillToRoadmap).toHaveBeenCalledWith('kafka', 7);
    expect(hrefOf('On your roadmap')).toBe('/roadmap');
    expect(screen.queryByText('Add to roadmap')).not.toBeInTheDocument();   // cannot be clicked twice
  });

  test('a duplicate reported by the server shows as already planned', async () => {
    skillService.addSkillToRoadmap.mockResolvedValue({ added: false, on_roadmap: true, message: 'already on your learning roadmap' });
    inRouter(<AddToRoadmapButton skill="kafka" />);
    fireEvent.click(screen.getByText('Add to roadmap'));
    expect(await screen.findByText('On your roadmap')).toBeInTheDocument();
  });

  test('skills already planned or verified are not offered', async () => {
    inRouter(<AddToRoadmapButton skill="sql" initiallyPlanned />);
    expect(screen.getByText('On your roadmap')).toBeInTheDocument();
    skillService.addSkillToRoadmap.mockResolvedValue({ added: false, verified: true, message: 'already verified' });
    inRouter(<AddToRoadmapButton skill="python" />);
    fireEvent.click(screen.getByText('Add to roadmap'));
    expect(await screen.findByText('Already verified')).toBeInTheDocument();
  });

  test('shows the server error', async () => {
    skillService.addSkillToRoadmap.mockRejectedValue({ response: { status: 400, data: { error: 'That skill is not listed for this job' } } });
    inRouter(<AddToRoadmapButton skill="rust" jobId={1} />);
    fireEvent.click(screen.getByText('Add to roadmap'));
    expect(await screen.findByText('That skill is not listed for this job')).toBeInTheDocument();
  });
});

const REQUEST = {
  id: 5, skill_name: 'sql', status: 'pending', status_label: 'Awaiting your answer', message: 'For our data role',
  organisation: { name: 'Acme Analytics', is_verified: true }, job_title: 'Data Engineer', skill_id: 42,
  skill_verified: false, seen: false, created_at: '2026-11-20T10:00:00+00:00',
  what_is_shared: 'Failed attempts and scores are not reported.'
};

describe('Student verification request item', () => {
  test('a pending request can be accepted or declined with a note', () => {
    const onRespond = jest.fn();
    inRouter(<VerificationRequestItem r={REQUEST} onRespond={onRespond} />);
    expect(screen.getByText('Acme Analytics')).toBeInTheDocument();
    expect(screen.getByText(/Failed attempts and scores are not reported/)).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText('Optional note to the employer'), { target: { value: 'Happy to' } });
    fireEvent.click(screen.getByText('Accept'));
    expect(onRespond).toHaveBeenCalledWith(REQUEST, 'accept', 'Happy to');
    expect(screen.queryByText('Take the assessment →')).not.toBeInTheDocument();   // nothing to do before consenting
  });

  test('an accepted request links to the quiz and to evidence for that skill', () => {
    inRouter(<VerificationRequestItem r={{ ...REQUEST, status: 'accepted', status_label: 'Accepted' }} onRespond={jest.fn()} />);
    expect(hrefOf('Take the assessment →')).toBe('/verify-skill/42');
    expect(hrefOf('Submit evidence for review →')).toBe('/skill-passport?evidence_for=42');
    expect(screen.queryByText('Accept')).not.toBeInTheDocument();
  });

  test('a completed request offers no actions', () => {
    inRouter(<VerificationRequestItem r={{ ...REQUEST, status: 'completed', status_label: 'Completed', skill_verified: true,
      completed_via_label: 'passed the SkillBridge assessment' }} onRespond={jest.fn()} />);
    expect(screen.getByText(/passed the SkillBridge assessment/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('Recruiter verification request panel', () => {
  const data = {
    can_request_verification: true,
    requestable_skills: [{ skill_name: 'sql', status_label: 'AI-extracted' }, { skill_name: 'rust', status_label: 'Self-declared' }],
    verification_requests: [{ id: 1, skill_name: 'docker', status: 'accepted', status_label: 'Accepted - candidate is verifying', created_at: '2026-11-20T10:00:00+00:00' }]
  };

  test('sends only the selected skills, with the job and message', async () => {
    const act = jest.fn((fn) => fn());
    recruiterService.requestSkillVerification.mockResolvedValue({ message: 'ok' });
    inRouter(<VerificationRequestsPanel data={data} candidateRef="ref123" jobId="9" act={act} />);
    const send = screen.getByText(/^Request verification/);
    expect(send).toBeDisabled();
    fireEvent.click(screen.getByText(/^SQL/i));
    fireEvent.change(screen.getByPlaceholderText(/Why you are asking/), { target: { value: 'Needed for the role' } });
    fireEvent.click(screen.getByText('Request verification (1)'));
    await waitFor(() => expect(recruiterService.requestSkillVerification).toHaveBeenCalledWith(
      'ref123', { skills: ['sql'], message: 'Needed for the role', job_id: 9 }));
    expect(screen.getByText('Accepted - candidate is verifying')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  test('explains when the organisation is not verified', () => {
    inRouter(<VerificationRequestsPanel data={{ ...data, can_request_verification: false }} candidateRef="r" act={jest.fn()} />);
    expect(screen.getByText(/once your organisation is verified/)).toBeInTheDocument();
    expect(screen.queryByText(/^Request verification/)).not.toBeInTheDocument();
  });
});

describe('Next-step logic', () => {
  test('readiness steps follow the weak parts of the score', () => {
    const steps = readinessSteps({
      career: 'Data Scientist', target_career_set: false, job_domain: 'Data Science',
      readiness: { breakdown: { required_skills_pct: 40, quiz_proficiency_pct: 50 } },
      gap_summary: { missing_required: ['statistics', 'sql'] }
    }).filter(Boolean);
    const to = steps.map((s) => s.to);
    expect(to).toEqual(expect.arrayContaining(['/careers', '/skill-gap', '/assessment', '/roadmap', '/jobs?domain=Data%20Science']));
    expect(steps.find((s) => s.to === '/skill-gap').detail).toMatch(/2 required skills/);

    const strong = readinessSteps({
      career: 'Data Scientist', target_career_set: true, job_domain: null,
      readiness: { breakdown: { required_skills_pct: 100, quiz_proficiency_pct: 90 } }, gap_summary: {}
    }).filter(Boolean).map((s) => s.to);
    expect(strong).not.toContain('/skill-gap');
    expect(strong).not.toContain('/assessment');
    expect(strong).toContain('/jobs?q=Data%20Scientist');
  });

  test('career recommendations link to their jobs domain', () => {
    expect(careerJobsLink({ career: 'Data Scientist', job_domain: 'Data Science' })).toBe('/jobs?domain=Data%20Science');
    expect(careerJobsLink({ career: 'Product Manager', job_domain: null })).toBe('/jobs?q=Product%20Manager');
  });

  test('roadmap skills link to verification and jobs', () => {
    const group = { skill: 'sql', skill_id: 3, verified: false, days: [{ id: 1, is_completed: true }] };
    inRouter(<SkillGroupActions group={group} />);
    expect(screen.getByText(/All days done/)).toBeInTheDocument();
    expect(hrefOf('Take the verification quiz')).toBe('/verify-skill/3');
    expect(hrefOf('Submit project evidence')).toBe('/skill-passport?evidence_for=3');
    expect(hrefOf('Jobs that need it')).toBe('/jobs?skill=sql');
    expect(categoryLabel('From job: Data Engineer')).toBe('From job: Data Engineer');
    expect(categoryLabel('Core')).toBe('Core skill');
  });

  test('assessment attempts: retake or study a failed skill, share a passed one', () => {
    const onRetake = jest.fn();
    inRouter(<AttemptNextStep attempt={{ skill_id: 4, skill_name: 'docker', passed: false }} onRetake={onRetake} />);
    fireEvent.click(screen.getByText('Retake'));
    expect(onRetake).toHaveBeenCalled();
    expect(screen.getByText('Add to roadmap')).toBeInTheDocument();
    inRouter(<AttemptNextStep attempt={{ skill_id: 5, skill_name: 'python', passed: true }} onRetake={onRetake} />);
    expect(hrefOf('Jobs using it')).toBe('/jobs?skill=python');
  });
});
