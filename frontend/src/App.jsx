import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProfileProvider } from './context/ProfileContext';
import ProtectedRoute from './components/common/ProtectedRoute';
import Loader from './components/common/Loader';

// Each page is its own chunk, fetched only when that route is visited —
// avoids shipping every page (and heavy deps like @vapi-ai/web, only
// needed by Voice) in the bundle the very first paint has to load.
const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Signup = lazy(() => import('./pages/Signup'));
const Analyze = lazy(() => import('./pages/Analyze'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Reflect = lazy(() => import('./pages/Reflect'));
const Chat = lazy(() => import('./pages/Chat'));
const Voice = lazy(() => import('./pages/Voice'));
const ModeSelect = lazy(() => import('./pages/ModeSelect'));
const Profiles = lazy(() => import('./pages/Profiles'));

export default function App() {
  return (
    <AuthProvider>
      <ProfileProvider>
        <Router>
          <Suspense fallback={<Loader fullPage text="Loading..." />}>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/analyze" element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/reflect" element={<ProtectedRoute><Reflect /></ProtectedRoute>} />
              <Route path="/mode" element={<ProtectedRoute><ModeSelect /></ProtectedRoute>} />
              <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
              <Route path="/voice" element={<ProtectedRoute><Voice /></ProtectedRoute>} />
              <Route path="/profiles" element={<ProtectedRoute><Profiles /></ProtectedRoute>} />
            </Routes>
          </Suspense>
        </Router>
      </ProfileProvider>
    </AuthProvider>
  );
}
