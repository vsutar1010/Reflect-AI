import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { UserPlus, Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Button from '../components/common/Button';
import Loader from '../components/common/Loader';
import ProfileGrid from '../components/features/profile/ProfileGrid';
import { useProfile } from '../context/ProfileContext';

export default function Profiles() {
  const { profiles, selectedProfile, selectProfile, removeProfile, fetchProfiles, loadingProfiles, error } =
    useProfile();

  return (
    <div className="relative min-h-screen bg-[#050505] text-[#F8FAFC] font-sans pb-24">
      {/* Background Glows */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[#4F8BFF]/10 blur-[150px]" />
        <div className="absolute top-[20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-[#8B5CF6]/10 blur-[150px]" />
      </div>

      <Navbar />

      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-36">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-12 border-b border-white/10 pb-8">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#4F8BFF]/30 bg-[#4F8BFF]/10 text-xs font-semibold text-[#4F8BFF] uppercase mb-3">
              <Sparkles className="w-3.5 h-3.5" /> Identity Registry
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">
              Digital Twin Profiles
            </h1>
            <p className="text-slate-400 text-sm mt-2 max-w-xl">
              Select an active digital clone to start chatting, or build a new twin personality using the 10-question analysis workflow.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              size="md"
              icon={RefreshCw}
              loading={loadingProfiles}
              onClick={fetchProfiles}
            >
              Refresh
            </Button>
            <Link to="/analyze">
              <Button variant="primary" size="md" icon={UserPlus}>
                Create Twin
              </Button>
            </Link>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-8 p-4 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Selected Twin Active Banner */}
        {selectedProfile && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-10 p-5 bg-gradient-to-r from-[#4F8BFF]/15 to-[#8B5CF6]/15 border border-[#4F8BFF]/30 rounded-3xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-[0_0_30px_rgba(79,139,255,0.1)]"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#4F8BFF] to-[#8B5CF6] flex items-center justify-center text-white font-bold text-lg shadow-md">
                {selectedProfile.name ? selectedProfile.name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div>
                <span className="text-xs font-semibold text-[#4F8BFF] uppercase tracking-wider block">
                  Currently Active Twin
                </span>
                <h3 className="text-lg font-bold text-white">{selectedProfile.name}</h3>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Link to="/dashboard">
                <Button variant="primary" size="sm">
                  View Dashboard
                </Button>
              </Link>
              <Link to="/chat">
                <Button variant="secondary" size="sm">
                  Start Chat
                </Button>
              </Link>
            </div>
          </motion.div>
        )}

        {/* Loading State */}
        {loadingProfiles && profiles.length === 0 ? (
          <Loader text="Loading profiles from server..." />
        ) : profiles.length === 0 ? (
          /* Empty State */
          <div className="bg-[#09090B]/60 backdrop-blur-xl border border-white/10 rounded-3xl p-12 text-center max-w-lg mx-auto my-12 space-y-6">
            <div className="w-16 h-16 rounded-3xl bg-[#4F8BFF]/10 text-[#4F8BFF] flex items-center justify-center mx-auto">
              <UserPlus className="w-8 h-8" />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-bold text-white">No Digital Twins Found</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                You haven't created any personality profiles yet. Run the 10-question analysis interview to generate your first AI twin.
              </p>
            </div>
            <Link to="/analyze" className="inline-block">
              <Button variant="primary" size="lg" icon={UserPlus}>
                Start Personality Analysis
              </Button>
            </Link>
          </div>
        ) : (
          /* Profiles Grid */
          <ProfileGrid
            profiles={profiles}
            selectedProfile={selectedProfile}
            onSelect={selectProfile}
            onDelete={removeProfile}
          />
        )}
      </main>
    </div>
  );
}
