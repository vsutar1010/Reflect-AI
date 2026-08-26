import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, User, UserPlus, ShieldCheck, ArrowLeft } from 'lucide-react';
import Card from '../components/common/Card';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import GoogleSignInButton from '../components/common/GoogleSignInButton';
import AnimatedBackground from '../components/common/AnimatedBackground';
import { useAuth } from '../context/AuthContext';

const RESEND_COOLDOWN_SECONDS = 60;

export default function Signup() {
  const { requestSignupOtp, verifySignupOtp } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState('details'); // 'details' | 'otp'
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const cooldownRef = useRef(null);

  useEffect(() => {
    return () => clearInterval(cooldownRef.current);
  }, []);

  const startCooldown = () => {
    setCooldown(RESEND_COOLDOWN_SECONDS);
    clearInterval(cooldownRef.current);
    cooldownRef.current = setInterval(() => {
      setCooldown((c) => {
        if (c <= 1) {
          clearInterval(cooldownRef.current);
          return 0;
        }
        return c - 1;
      });
    }, 1000);
  };

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      await requestSignupOtp(email, password, name);
      setStep('otp');
      startCooldown();
    } catch (err) {
      setError(err.message || 'Signup failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await verifySignupOtp(email, otp);
      navigate('/mode', { replace: true });
    } catch (err) {
      setError(err.message || 'Verification failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setError('');
    try {
      await requestSignupOtp(email, password, name);
      startCooldown();
    } catch (err) {
      setError(err.message || 'Could not resend code.');
    }
  };

  return (
    <div className="relative min-h-screen bg-[#050505] text-[#F8FAFC] flex items-center justify-center px-6 py-24 overflow-hidden">
      <AnimatedBackground />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <Link to="/" className="flex items-center justify-center gap-2 text-xl font-bold text-white mb-8">
          <span className="w-3 h-3 rounded-full bg-gradient-to-r from-[#4F8BFF] to-[#8B5CF6] shadow-[0_0_10px_#4F8BFF]" />
          Reflect<span className="text-[#4F8BFF]">AI</span>
        </Link>

        <Card className="w-full">
          {step === 'details' ? (
            <>
              <h1 className="text-2xl font-bold text-white mb-1 text-center">Create your account</h1>
              <p className="text-sm text-slate-400 mb-6 text-center">
                Twins you create will only ever be visible to you.
              </p>

              <form onSubmit={handleRequestOtp} className="flex flex-col gap-4">
                <Input
                  id="name"
                  type="text"
                  label="Name"
                  icon={User}
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
                <Input
                  id="email"
                  type="email"
                  label="Email"
                  icon={Mail}
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <Input
                  id="password"
                  type="password"
                  label="Password"
                  icon={Lock}
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />

                {error && <p className="text-xs text-red-400 font-medium text-center">{error}</p>}

                <Button type="submit" variant="primary" size="lg" loading={loading} icon={UserPlus} className="w-full mt-2">
                  Send Verification Code
                </Button>
              </form>

              <div className="flex items-center gap-3 my-6">
                <div className="flex-1 h-px bg-white/10" />
                <span className="text-xs text-slate-500 uppercase tracking-wider">or</span>
                <div className="flex-1 h-px bg-white/10" />
              </div>

              <GoogleSignInButton onError={setError} />

              <p className="text-sm text-slate-400 text-center mt-6">
                Already have an account?{' '}
                <Link to="/login" className="text-[#4F8BFF] font-semibold hover:underline">
                  Log in
                </Link>
              </p>
            </>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-white mb-1 text-center">Check your email</h1>
              <p className="text-sm text-slate-400 mb-6 text-center">
                We sent a 6-digit code to <span className="text-slate-200 font-medium">{email}</span>.
              </p>

              <form onSubmit={handleVerifyOtp} className="flex flex-col gap-4">
                <Input
                  id="otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  label="Verification code"
                  icon={ShieldCheck}
                  placeholder="123456"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                />

                {error && <p className="text-xs text-red-400 font-medium text-center">{error}</p>}

                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  loading={loading}
                  icon={ShieldCheck}
                  disabled={otp.length !== 6}
                  className="w-full mt-2"
                >
                  Verify & Create Account
                </Button>
              </form>

              <div className="flex items-center justify-between mt-6 text-sm">
                <button
                  onClick={() => {
                    setStep('details');
                    setError('');
                  }}
                  className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Edit details
                </button>

                <button
                  onClick={handleResend}
                  disabled={cooldown > 0}
                  className="text-[#4F8BFF] font-semibold hover:underline disabled:text-slate-600 disabled:no-underline disabled:cursor-not-allowed"
                >
                  {cooldown > 0 ? `Resend code (${cooldown}s)` : 'Resend code'}
                </button>
              </div>
            </>
          )}
        </Card>
      </motion.div>
    </div>
  );
}
