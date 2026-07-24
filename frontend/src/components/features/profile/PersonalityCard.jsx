import React from 'react';
import Card from '../../common/Card';
import { Sparkles, Tag, Heart, Zap, MessageSquare } from 'lucide-react';

export default function PersonalityCard({ profileData }) {
  if (!profileData) return null;

  const { identity, personality, communication } = profileData;
  const p = profileData.profile || profileData; // supports root or wrapped profile format

  return (
    <Card className="space-y-6">
      <div className="flex items-center gap-2 pb-4 border-b border-white/10">
        <Sparkles className="w-5 h-5 text-[#8B5CF6]" />
        <h3 className="font-bold text-white text-lg">Personality Dimensions</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Core Attributes */}
        <div className="space-y-3">
          <div className="bg-white/5 p-3 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold block uppercase">Tone</span>
            <span className="text-sm font-medium text-white">{p.tone || 'Balanced'}</span>
          </div>

          <div className="bg-white/5 p-3 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold block uppercase">Communication Style</span>
            <span className="text-sm font-medium text-white">{p.communication_style || 'Direct & Articulate'}</span>
          </div>

          <div className="bg-white/5 p-3 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold block uppercase">Humor</span>
            <span className="text-sm font-medium text-white">{p.humor || 'Witty / Subtle'}</span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="bg-white/5 p-3 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold block uppercase">Directness & Energy</span>
            <span className="text-sm font-medium text-white">{p.directness || 'High'} / {p.energy || 'Moderate'}</span>
          </div>

          <div className="bg-white/5 p-3 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold block uppercase">Sentence Structure</span>
            <span className="text-sm font-medium text-white">{p.sentence_length || 'Concise & Structured'}</span>
          </div>

          <div className="bg-white/5 p-3 rounded-xl">
            <span className="text-xs text-slate-400 font-semibold block uppercase">Confidence Level</span>
            <span className="text-sm font-medium text-white">{p.confidence || 'Assertive'}</span>
          </div>
        </div>
      </div>

      {/* Preferred Topics */}
      {p.preferred_topics && p.preferred_topics.length > 0 && (
        <div className="pt-2">
          <span className="text-xs text-slate-400 font-semibold uppercase block mb-2 flex items-center gap-1.5">
            <Tag className="w-3.5 h-3.5 text-[#4F8BFF]" /> Preferred Topics
          </span>
          <div className="flex flex-wrap gap-2">
            {p.preferred_topics.map((topic, i) => (
              <span
                key={i}
                className="px-3 py-1 bg-[#4F8BFF]/10 text-[#4F8BFF] border border-[#4F8BFF]/20 rounded-full text-xs font-medium"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Values */}
      {p.values && p.values.length > 0 && (
        <div className="pt-1">
          <span className="text-xs text-slate-400 font-semibold uppercase block mb-2 flex items-center gap-1.5">
            <Heart className="w-3.5 h-3.5 text-[#8B5CF6]" /> Core Values
          </span>
          <div className="flex flex-wrap gap-2">
            {p.values.map((val, i) => (
              <span
                key={i}
                className="px-3 py-1 bg-[#8B5CF6]/10 text-[#8B5CF6] border border-[#8B5CF6]/20 rounded-full text-xs font-medium"
              >
                {val}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {p.summary && (
        <div className="bg-white/5 p-4 rounded-2xl border border-white/5 text-xs text-slate-300 leading-relaxed italic">
          "{p.summary}"
        </div>
      )}
    </Card>
  );
}
