import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function GoogleSignInButton({ onError }) {
  const { loginWithGoogle } = useAuth();
  const buttonRef = useRef(null);
  const [scriptReady, setScriptReady] = useState(!!window.google?.accounts?.id);

  useEffect(() => {
    if (!CLIENT_ID || scriptReady) return;

    const existing = document.getElementById('google-identity-script');
    const script = existing || document.createElement('script');
    if (!existing) {
      script.id = 'google-identity-script';
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
    script.addEventListener('load', () => setScriptReady(true));
  }, [scriptReady]);

  useEffect(() => {
    if (!CLIENT_ID || !scriptReady || !buttonRef.current || !window.google?.accounts?.id) return;

    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: async (response) => {
        try {
          await loginWithGoogle(response.credential);
        } catch (err) {
          onError?.(err.message || 'Google sign-in failed.');
        }
      },
    });

    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: 'filled_black',
      size: 'large',
      shape: 'pill',
      width: 320,
    });
  }, [scriptReady, loginWithGoogle, onError]);

  if (!CLIENT_ID) return null;

  return <div ref={buttonRef} className="flex justify-center w-full" />;
}
