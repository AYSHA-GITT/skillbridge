import api from './api';

export const authService = {
  login: async (email, password, portal = null) => {
    const payload = { email, password };
    if (portal) {
      payload.portal = portal;
    }
    const response = await api.post('/auth/login', payload);
    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data.student;
  },

  getPrivacyInfo: async () => {
    const response = await api.get('/student/privacy_info');
    return response.data;
  }
};

export default authService;
