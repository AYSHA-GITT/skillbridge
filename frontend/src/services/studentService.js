import api from './api';

export const getRoadmap = async () => {
  const response = await api.get('/student/get_roadmap');
  return response.data;
};

export const generateRoadmap = async () => {
  const response = await api.post('/student/generate_roadmap');
  return response.data;
};

export const completeRoadmapDay = async (planId) => {
  const response = await api.post(
    `/student/complete_roadmap_day/${planId}`
  );
  return response.data;
};