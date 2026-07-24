import React from 'react';
import Card from '../../common/Card';

export default function StatCard({ icon: Icon, label, value, subtext, color = 'blue' }) {
  const colorMap = {
    blue: 'bg-[#4F8BFF]/10 text-[#4F8BFF] border-[#4F8BFF]/20',
    purple: 'bg-[#8B5CF6]/10 text-[#8B5CF6] border-[#8B5CF6]/20',
    green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  };

  return (
    <Card className="flex items-center gap-4">
      {Icon && (
        <div className={`p-3 rounded-2xl border ${colorMap[color] || colorMap.blue}`}>
          <Icon className="w-6 h-6" />
        </div>
      )}
      <div>
        <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">{label}</span>
        <span className="text-xl font-extrabold text-white">{value}</span>
        {subtext && <span className="text-xs text-slate-500 block mt-0.5">{subtext}</span>}
      </div>
    </Card>
  );
}
