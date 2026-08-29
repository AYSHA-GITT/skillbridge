import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import UploadResume from './pages/UploadResume';
import ProcessResume from './pages/ProcessResume';
import VerifySkill from './pages/VerifySkill';
import SkillProfile from './pages/SkillProfile';
import SkillGap from './pages/SkillGap';
import SkillGapResults from './pages/SkillGapResults';
import Assessment from './pages/Assessment';
import Roadmap from './pages/Roadmap';
import Readiness from './pages/Readiness';
import Progress from './pages/Progress';
import SalarySim from './pages/SalarySim';
import Badges from './pages/Badges';
import Company from './pages/Company';
import FedViz from './pages/FedViz';
import Admin from './pages/Admin';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Student Workflow Routes */}
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/upload-resume" element={<UploadResume />} />
        <Route path="/process-resume/:resumeId" element={<ProcessResume />} />
        <Route path="/verify-skill/:skillId" element={<VerifySkill />} />

        {/* Intelligence & Analytics Views */}
        <Route path="/profile" element={<SkillProfile />} />
        <Route path="/skill-gap" element={<SkillGap />} />
        <Route path="/skill-gap-results" element={<SkillGapResults />} />
        <Route path="/assessment" element={<Assessment />} />
        <Route path="/roadmap" element={<Roadmap />} />
        <Route path="/readiness" element={<Readiness />} />
        <Route path="/progress" element={<Progress />} />
        <Route path="/salary-sim" element={<SalarySim />} />
        <Route path="/badges" element={<Badges />} />
        <Route path="/careers" element={<Company />} />

        {/* Federated Learning & Admin Views */}
        <Route path="/federated" element={<FedViz />} />
        <Route path="/admin" element={<Admin />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;