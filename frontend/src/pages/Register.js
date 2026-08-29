import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '', email: '', password: '', college: '', course: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/register', form);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="glass w-full max-w-md p-8">
        <h1 className="font-heading text-3xl font-semibold mb-1">
          Create your account
        </h1>
        <p className="text-white/50 text-sm mb-8">
          Start your personalized career journey
        </p>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="text" name="name" placeholder="Full name" className="input-field" value={form.name} onChange={handleChange} required />
          <input type="email" name="email" placeholder="Email address" className="input-field" value={form.email} onChange={handleChange} required />
          <input type="password" name="password" placeholder="Password" className="input-field" value={form.password} onChange={handleChange} required />
          <input type="text" name="college" placeholder="College name" className="input-field" value={form.college} onChange={handleChange} required />
          <input type="text" name="course" placeholder="Course (e.g. B.Tech CSE)" className="input-field" value={form.course} onChange={handleChange} required />
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-white/40 text-sm mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-accent-400 hover:text-accent-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}