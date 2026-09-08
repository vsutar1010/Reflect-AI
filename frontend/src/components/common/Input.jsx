import React from 'react';

export default function Input({
  label,
  error,
  icon: Icon,
  rightSlot,
  className = '',
  id,
  ...props
}) {
  return (
    <div className="flex flex-col gap-1.5 w-full text-left">
      {label && (
        <label htmlFor={id} className="text-xs font-semibold text-slate-300 tracking-wide uppercase">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {Icon && (
          <div className="absolute left-3.5 text-slate-400 pointer-events-none">
            <Icon className="w-4 h-4" />
          </div>
        )}
        <input
          id={id}
          className={`w-full bg-white/5 border ${
            error ? 'border-red-500/50 focus:border-red-500' : 'border-white/10 focus:border-[#4F8BFF]'
          } rounded-xl ${Icon ? 'pl-10' : 'px-4'} ${rightSlot ? 'pr-11' : ''} py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 ${
            error ? 'focus:ring-red-500/30' : 'focus:ring-[#4F8BFF]/30'
          } transition-all duration-200 ${className}`}
          {...props}
        />
        {rightSlot && <div className="absolute right-3">{rightSlot}</div>}
      </div>
      {error && <span className="text-xs text-red-400 font-medium">{error}</span>}
    </div>
  );
}
