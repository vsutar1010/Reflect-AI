import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProfileProvider } from './context/ProfileContext';
import ProtectedRoute from './components/common/ProtectedRoute';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Analyze from './pages/Analyze';
import Dashboard from './pages/Dashboard';
import Reflect from './pages/Reflect';
import Chat from './pages/Chat';
import Voice from './pages/Voice';
import ModeSelect from './pages/ModeSelect';
import Profiles from './pages/Profiles';

export default function App() {
  return (
    <AuthProvider>
      <ProfileProvider>
        <Router>
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
        </Router>
      </ProfileProvider>
    </AuthProvider>
  );
}
