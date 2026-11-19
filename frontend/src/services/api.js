import axios from 'axios';

const api = axios.create({
  // Production builds talk to the same origin (the reverse proxy forwards /api to Flask).
  baseURL: process.env.REACT_APP_API_URL
    || (process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:5000/api'),
  withCredentials: true, // sends session cookies automatically
});

export default api;