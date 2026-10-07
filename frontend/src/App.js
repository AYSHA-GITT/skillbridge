import React from 'react';
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
import { ProtectedRoute, AdminRoute } from './components/RouteGuards';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ============================================================ */}
        {/* PUBLIC ENTRY ROUTES */}
        {/* ============================================================ */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* ============================================================ */}
        {/* PROTECTED STUDENT PORTAL ROUTES */}
        {/* ============================================================ */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/upload-resume"
          element={
            <ProtectedRoute>
              <UploadResume />
            </ProtectedRoute>
          }
        />
        <Route
          path="/process-resume/:resumeId"
          element={
            <ProtectedRoute>
              <ProcessResume />
            </ProtectedRoute>
          }
        />
        <Route
          path="/verify-skill/:skillId"
          element={
            <ProtectedRoute>
              <VerifySkill />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <SkillProfile />
            </ProtectedRoute>
          }
        />
        <Route
          path="/skill-gap"
          element={
            <ProtectedRoute>
              <SkillGap />
            </ProtectedRoute>
          }
        />
        <Route
          path="/skill-gap-results"
          element={
            <ProtectedRoute>
              <SkillGapResults />
            </ProtectedRoute>
          }
        />
        <Route
          path="/assessment"
          element={
            <ProtectedRoute>
              <Assessment />
            </ProtectedRoute>
          }
        />
        <Route
          path="/roadmap"
          element={
            <ProtectedRoute>
              <Roadmap />
            </ProtectedRoute>
          }
        />
        <Route
          path="/readiness"
          element={
            <ProtectedRoute>
              <Readiness />
            </ProtectedRoute>
          }
        />
        <Route
          path="/progress"
          element={
            <ProtectedRoute>
              <Progress />
            </ProtectedRoute>
          }
        />
        <Route
          path="/salary-sim"
          element={
            <ProtectedRoute>
              <SalarySim />
            </ProtectedRoute>
          }
        />
        <Route
          path="/badges"
          element={
            <ProtectedRoute>
              <Badges />
            </ProtectedRoute>
          }
        />
        <Route
          path="/careers"
          element={
            <ProtectedRoute>
              <Company />
            </ProtectedRoute>
          }
        />

        {/* ============================================================ */}
        {/* INSTITUTION / ADMIN PORTAL (ADMIN PRIVILEGES REQUIRED) */}
        {/* ============================================================ */}
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <Admin />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/*"
          element={
            <AdminRoute>
              <Admin />
            </AdminRoute>
          }
        />

        {/* Legacy /federated redirected to Admin FL Center with Admin protection */}
        <Route
          path="/federated"
          element={
            <AdminRoute>
              <FedViz />
            </AdminRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;