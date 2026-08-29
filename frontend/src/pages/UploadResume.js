import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function UploadResume() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [resumeId, setResumeId] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setStatus('idle');
    setMessage('');
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setMessage('Please choose a PDF or DOCX file first');
      setStatus('error');
      return;
    }
    setStatus('uploading');
    setMessage('');
    const formData = new FormData();
    formData.append('resume', file);
    try {
      const res = await api.post('/student/upload_resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResumeId(res.data.resume.id);
      setStatus('done');
      setMessage('Resume uploaded successfully!');
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.error || 'Upload failed');
    }
  };

  return (
    <div className="min-h-screen px-6 py-10 max-w-2xl mx-auto">
      <button onClick={() => navigate('/dashboard')} className="text-white/40 hover:text-white text-sm mb-6">
        ← Back to dashboard
      </button>

      <div className="glass p-8">
        <h1 className="font-heading text-2xl font-semibold mb-1">Upload your resume</h1>
        <p className="text-white/50 text-sm mb-8">PDF or DOCX only. We'll extract your skills automatically.</p>

        {message && (
          <div className={`mb-4 px-4 py-3 rounded-xl text-sm border ${
            status === 'error'
              ? 'bg-red-500/10 border-red-500/20 text-red-400'
              : 'bg-accent-400/10 border-accent-400/20 text-accent-400'
          }`}>
            {message}
          </div>
        )}

        <form onSubmit={handleUpload} className="space-y-5">
          <label className="block">
            <div className="border-2 border-dashed border-white/15 rounded-xl p-8 text-center hover:border-accent-400/40 transition-all cursor-pointer">
              <input type="file" accept=".pdf,.docx" onChange={handleFileChange} className="hidden" />
              <p className="text-white/60 text-sm">{file ? file.name : 'Click to choose a file'}</p>
            </div>
          </label>
          <button type="submit" className="btn-primary" disabled={status === 'uploading'}>
            {status === 'uploading' ? 'Uploading...' : 'Upload Resume'}
          </button>
        </form>

        {status === 'done' && resumeId && (
          <button
            onClick={() => navigate(`/process-resume/${resumeId}`)}
            className="w-full mt-4 px-4 py-3 rounded-xl border border-accent-400/30 text-accent-400 hover:bg-accent-400/10 transition-all text-sm font-medium"
          >
            Continue → Parse & Extract Skills
          </button>
        )}
      </div>
    </div>
  );
}