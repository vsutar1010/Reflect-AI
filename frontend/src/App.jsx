import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ProfileProvider } from './context/ProfileContext';
import Landing from './pages/Landing';
import Analyze from './pages/Analyze';
import Dashboard from './pages/Dashboard';
import Reflect from './pages/Reflect';
import Chat from './pages/Chat';
import Voice from './pages/Voice';
import ModeSelect from './pages/ModeSelect';
import Profiles from './pages/Profiles';

export default function App() {
  return (
    <ProfileProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/analyze" element={<Analyze />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/reflect" element={<Reflect />} />
          <Route path="/mode" element={<ModeSelect />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/voice" element={<Voice />} />
          <Route path="/profiles" element={<Profiles />} />
        </Routes>
      </Router>
    </ProfileProvider>
  );
}
