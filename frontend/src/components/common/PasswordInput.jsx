import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import Input from './Input';

// A password field with a show/hide toggle, built on the shared Input
// component so it inherits the exact same visual style everywhere it's
// used (Login, and the new Forgot Password flow). Hidden by default.
export default function PasswordInput(props) {
  const [visible, setVisible] = useState(false);

  return (
    <Input
      {...props}
      type={visible ? 'text' : 'password'}
      rightSlot={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          tabIndex={-1}
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          className="text-slate-400 hover:text-white transition-colors p-0.5"
        >
          {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      }
    />
  );
}
