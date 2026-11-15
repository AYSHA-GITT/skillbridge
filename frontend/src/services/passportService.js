import api from './api';

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const filenameFrom = (response, fallback) => {
  const cd = response.headers?.['content-disposition'] || '';
  const m = cd.match(/filename="?([^"]+)"?/);
  return m ? m[1] : fallback;
};

export const passportService = {
  // Owner view
  getMyPassport: async () => (await api.get('/passport/me')).data,
  updateProfile: async (profile) => (await api.put('/passport/me/profile', profile)).data,

  addSkill: async (skillName) => (await api.post('/passport/me/skills', { skill_name: skillName })).data,
  removeSkill: async (skillId) => (await api.delete(`/passport/me/skills/${skillId}`)).data,

  createEvidence: async (payload) => (await api.post('/passport/me/evidence', payload)).data,
  updateEvidence: async (id, payload) => (await api.put(`/passport/me/evidence/${id}`, payload)).data,
  deleteEvidence: async (id) => (await api.delete(`/passport/me/evidence/${id}`)).data,
  requestReview: async (id) => (await api.post(`/passport/me/evidence/${id}/request_review`)).data,
  uploadEvidenceFile: async (id, file) => {
    const form = new FormData();
    form.append('file', file);
    return (await api.post(`/passport/me/evidence/${id}/file`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })).data;
  },
  downloadEvidenceFile: async (id, filename) => {
    const res = await api.get(`/passport/me/evidence/${id}/file`, { responseType: 'blob' });
    downloadBlob(res.data, filenameFrom(res, filename || 'evidence'));
  },
  importFromResume: async (items) => (await api.post('/passport/me/evidence/import', { items })).data,

  exportPdf: async (sections, skillFilter) => {
    const params = {};
    if (sections) params.sections = sections.join(',');
    if (skillFilter) params.skill_filter = skillFilter;
    const res = await api.get('/passport/me/pdf', { params, responseType: 'blob' });
    downloadBlob(res.data, filenameFrom(res, 'SkillPassport.pdf'));
  },

  // Sharing
  createShare: async (payload) => (await api.post('/passport/me/shares', payload)).data,
  revokeShare: async (id) => (await api.post(`/passport/me/shares/${id}/revoke`)).data,
  getAccessLog: async (id) => (await api.get(`/passport/me/shares/${id}/access_log`)).data,

  // Public (no login)
  getPublicPassport: async (token) => (await api.get(`/passport/public/${encodeURIComponent(token)}`)).data,
  publicPdfUrl: (token) => `${api.defaults.baseURL}/passport/public/${encodeURIComponent(token)}/pdf`,

  // Admin review
  adminListEvidence: async (status = 'pending') =>
    (await api.get('/passport/admin/evidence', { params: { status } })).data,
  adminReviewEvidence: async (id, decision, note) =>
    (await api.post(`/passport/admin/evidence/${id}/review`, { decision, note })).data,
  adminDownloadEvidenceFile: async (id, filename) => {
    const res = await api.get(`/passport/admin/evidence/${id}/file`, { responseType: 'blob' });
    downloadBlob(res.data, filenameFrom(res, filename || 'evidence'));
  },

  downloadBlob,
};

export default passportService;
