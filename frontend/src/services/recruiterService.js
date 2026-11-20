import api from './api';
import { apiErrorMessage } from '../utils/apiErrors';

const d = (p) => p.then((r) => r.data);

/** Recruiter portal (role = recruiter). Every call is authorised again on the server. */
export const recruiterService = {
  register: (payload) => d(api.post('/auth/register_recruiter', payload)),

  me: () => d(api.get('/recruiter/me')),
  dashboard: () => d(api.get('/recruiter/dashboard')),
  updateProfile: (payload) => d(api.put('/recruiter/me/profile', payload)),
  updateOrganisation: (payload) => d(api.put('/recruiter/organisation', payload)),
  requestVerification: (payload) => d(api.post('/recruiter/organisation/verification', payload)),

  listJobs: () => d(api.get('/recruiter/jobs')),
  getJob: (id) => d(api.get(`/recruiter/jobs/${id}`)),
  createJob: (payload) => d(api.post('/recruiter/jobs', payload)),
  updateJob: (id, payload) => d(api.put(`/recruiter/jobs/${id}`, payload)),
  publishJob: (id) => d(api.post(`/recruiter/jobs/${id}/publish`)),
  closeJob: (id) => d(api.post(`/recruiter/jobs/${id}/close`)),
  deleteJob: (id) => d(api.delete(`/recruiter/jobs/${id}`)),
  applicants: (id, stage) => d(api.get(`/recruiter/jobs/${id}/applicants`, { params: stage ? { stage } : {} })),
  jobMatches: (id) => d(api.get(`/recruiter/jobs/${id}/matches`)),

  searchCandidates: (params) => d(api.get('/recruiter/candidates/search', { params })),
  candidate: (ref, jobId) => d(api.get(`/recruiter/candidates/${encodeURIComponent(ref)}`, {
    params: jobId ? { job_id: jobId } : {}
  })),
  addNote: (ref, payload) => d(api.post(`/recruiter/candidates/${encodeURIComponent(ref)}/notes`, payload)),
  deleteNote: (id) => d(api.delete(`/recruiter/notes/${id}`)),
  invite: (ref, jobId, message) =>
    d(api.post(`/recruiter/candidates/${encodeURIComponent(ref)}/invite`, { job_id: jobId, message })),
  // Skill verification requests (the candidate decides; completion uses the passport "verified" rule)
  requestSkillVerification: (ref, payload) =>
    d(api.post(`/recruiter/candidates/${encodeURIComponent(ref)}/verification_requests`, payload)),
  verificationRequests: (status) => d(api.get('/recruiter/verification_requests', { params: status ? { status } : {} })),
  markVerificationRequestsRead: () => d(api.post('/recruiter/verification_requests/read')),
  cancelVerificationRequest: (id) => d(api.post(`/recruiter/verification_requests/${id}/cancel`)),

  listShortlists: () => d(api.get('/recruiter/shortlists')),
  getShortlist: (id) => d(api.get(`/recruiter/shortlists/${id}`)),
  createShortlist: (payload) => d(api.post('/recruiter/shortlists', payload)),
  deleteShortlist: (id) => d(api.delete(`/recruiter/shortlists/${id}`)),
  addToShortlist: (id, ref, note) => d(api.post(`/recruiter/shortlists/${id}/entries`, { candidate_ref: ref, note })),
  removeFromShortlist: (id, entryId) => d(api.delete(`/recruiter/shortlists/${id}/entries/${entryId}`)),

  pipeline: (jobId) => d(api.get('/recruiter/pipeline', { params: jobId ? { job_id: jobId } : {} })),
  changeStage: (appId, stage, message) => d(api.post(`/recruiter/applications/${appId}/stage`, { stage, message })),

  // Administrator: organisation verification
  adminOrganisations: (status = 'pending') => d(api.get('/recruiter/admin/organisations', { params: { status } })),
  adminReviewOrganisation: (id, decision, note) =>
    d(api.post(`/recruiter/admin/organisations/${id}/review`, { decision, note }))
};

/** Student side of the recruiter portal (role = student). */
export const candidateService = {
  getDiscovery: () => d(api.get('/candidate/discovery')),
  updateDiscovery: (payload) => d(api.put('/candidate/discovery', payload)),
  getAccess: () => d(api.get('/candidate/access')),
  getUpdates: () => d(api.get('/candidate/updates')),
  markUpdatesRead: () => d(api.post('/candidate/updates/read')),
  unreadCount: () => d(api.get('/candidate/updates/unread_count')),
  verificationRequests: () => d(api.get('/candidate/verification_requests')),
  respondVerificationRequest: (id, action, note) =>
    d(api.post(`/candidate/verification_requests/${id}/respond`, { action, note })),
  readinessPreview: () => d(api.get('/candidate/readiness_preview'))
};

// Server message first; otherwise says whether the server was unreachable, rate-limited or failed
export const errorText = (e, fallback = 'Something went wrong.') => apiErrorMessage(e, fallback);

export default recruiterService;
