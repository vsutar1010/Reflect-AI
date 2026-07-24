import React from 'react';
import { Link } from 'react-router-dom';
import { Plus, UserPlus } from 'lucide-react';
import ProfileCard from './ProfileCard';
import Card from '../../common/Card';

export default function ProfileGrid({ profiles, selectedProfile, onSelect, onDelete }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {/* Create New Twin Card */}
      <Link to="/analyze">
        <Card
          hover
          className="h-full min-h-[220px] flex flex-col items-center justify-center border-dashed border-white/20 hover:border-[#4F8BFF] bg-[#09090B]/30 hover:bg-[#4F8BFF]/5 text-center group transition-all duration-300"
        >
          <div className="w-12 h-12 rounded-full bg-white/5 group-hover:bg-[#4F8BFF]/20 flex items-center justify-center text-slate-300 group-hover:text-[#4F8BFF] mb-3 transition-colors">
            <Plus className="w-6 h-6" />
          </div>
          <h4 className="font-bold text-white text-base mb-1">Create New Digital Twin</h4>
          <p className="text-xs text-slate-400 max-w-[200px]">
            Run a 10-question analysis to clone another personality.
          </p>
        </Card>
      </Link>

      {/* Render Profile Cards */}
      {profiles.map((profile) => (
        <ProfileCard
          key={profile.id}
          profile={profile}
          isActive={selectedProfile?.id === profile.id}
          onSelect={onSelect}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
