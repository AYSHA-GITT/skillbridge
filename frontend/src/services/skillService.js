import api from './api';

export const skillService = {
  // Resume & Skills Extraction
  uploadResume: async (formData) => {
    const response = await api.post('/student/upload_resume', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  parseResume: async (resumeId) => {
    const response = await api.post(`/student/parse_resume/${resumeId}`);
    return response.data;
  },

  extractSkills: async (resumeId) => {
    const response = await api.post(`/student/extract_skills/${resumeId}`);
    return response.data;
  },

  getStudentSkills: async () => {
    const response = await api.get('/student/skills');
    return response.data;
  },

  // Assessments & Verification Quizzes
  getQuiz: async (skillId) => {
    const response = await api.get(`/student/get_quiz/${skillId}`);
    return response.data;
  },

  submitQuiz: async (skillId, answers) => {
    const response = await api.post(`/student/submit_quiz/${skillId}`, { answers });
    return response.data;
  },

  getAssessments: async () => {
    const response = await api.get('/student/assessments');
    return response.data;
  },

  // Career, Skill Gap & Readiness
  setTargetCareer: async (targetCareer) => {
    const response = await api.post('/student/set_target_career', { target_career: targetCareer });
    return response.data;
  },

  analyzeSkillGap: async () => {
    const response = await api.post('/student/analyze_skill_gap');
    return response.data;
  },

  getReadinessBreakdown: async () => {
    const response = await api.get('/student/readiness_breakdown');
    return response.data;
  },

  // Roadmap & Learning
  generateRoadmap: async () => {
    const response = await api.post('/student/generate_roadmap');
    return response.data;
  },

  getRoadmap: async () => {
    const response = await api.get('/student/get_roadmap');
    return response.data;
  },

  completeRoadmapDay: async (planId) => {
    const response = await api.post(`/student/complete_roadmap_day/${planId}`);
    return response.data;
  },

  // Progress & Badges
  getProgressHistory: async () => {
    const response = await api.get('/student/progress_history');
    return response.data;
  },

  getBadges: async () => {
    const response = await api.get('/student/badges');
    return response.data;
  },

  // Salary Simulation & Career Insights
  simulateSalary: async (additionalSkills = []) => {
    const response = await api.post('/student/simulate_salary', { additional_skills: additionalSkills });
    return response.data;
  },

  getCareerInsights: async () => {
    const response = await api.get('/student/career_insights');
    return response.data;
  },

  // Admin & Federated Learning
  getAdminStats: async () => {
    const response = await api.get('/admin/stats');
    return response.data;
  },

  triggerFLRound: async () => {
    const response = await api.post('/admin/federated/train');
    return response.data;
  },

  getFLRounds: async () => {
    const response = await api.get('/admin/federated/rounds');
    return response.data;
  },

  getFLNodes: async () => {
    const response = await api.get('/admin/federated/nodes');
    return response.data;
  }
};

export default skillService;
