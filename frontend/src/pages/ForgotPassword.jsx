import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, ShieldCheck, ArrowLeft, CheckCircle2, KeyRound } from 'lucide-react';
import Card from '../components/common/Card';
import Input from '../components/common/Input';
import PasswordInput from '../components/common/PasswordInput';
import Button from '../components/common/Button';
import AnimatedBackground from '../components/common/AnimatedBackground';
import { api } from '../services/api';

const RESEND_COOLDOWN_SECONDS = 60;

// A self-contained multi-step flow — doesn't touch AuthContext at all,
// since none of these steps change the logged-in user (a successful
// reset just returns the user to /login to sign in with the new
// password), matching how AuthContext only wraps calls that also need
// to update `user` state.
export default function ForgotPassword() {
  const navigate = useNavigate();

  const [step, setStep] = useState('email'); // 'email' | 'otp' | 'password' | 'success'
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

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

  const handleSendCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.requestPasswordReset(email);
      setStep('otp');
      startCooldown();
    } catch (err) {
      setError(err.message || 'Could not send reset code.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setError('');
    try {
      await api.requestPasswordReset(email);
      startCooldown();
    } catch (err) {
      setError(err.message || 'Could not resend code.');
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.verifyPasswordResetCode(email, otp);
      setStep('password');
    } catch (err) {
      setError(err.message || 'Invalid or expired code.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await api.resetPassword(email, otp, newPassword);
      setStep('success');
    } catch (err) {
      setError(err.message || 'Could not reset password.');
    } finally {
      setLoading(false);
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
          {step === 'email' && (
            <>
              <h1 className="text-2xl font-bold text-white mb-1 text-center">Reset your password</h1>
              <p className="text-sm text-slate-400 mb-6 text-center">
                Enter your account email and we'll send you a verification code.
              </p>

              <form onSubmit={handleSendCode} className="flex flex-col gap-4">
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

                {error && <p className="text-xs text-red-400 font-medium text-center">{error}</p>}

                <Button type="submit" variant="primary" size="lg" loading={loading} icon={Mail} className="w-full mt-2">
                  Send Code
                </Button>
              </form>

              <p className="text-sm text-slate-400 text-center mt-6">
                Remembered your password?{' '}
                <Link to="/login" className="text-[#4F8BFF] font-semibold hover:underline">
                  Log in
                </Link>
              </p>
            </>
          )}

          {step === 'otp' && (
            <>
              <h1 className="text-2xl font-bold text-white mb-1 text-center">Check your email</h1>
              <p className="text-sm text-slate-400 mb-6 text-center">
                We sent a 6-digit code to <span className="text-slate-200 font-medium">{email}</span>.
              </p>

              <form onSubmit={handleVerifyCode} className="flex flex-col gap-4">
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
                  onChange={(e) => {
                    setError('');
                    setOtp(e.target.value.replace(/\D/g, '').slice(0, 6));
                  }}
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
                  Verify Code
                </Button>
              </form>

              <div className="flex items-center justify-between mt-6 text-sm">
                <button
                  onClick={() => {
                    setStep('email');
                    setOtp('');
                    setError('');
                  }}
                  className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Edit email
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

          {step === 'password' && (
            <>
              <h1 className="text-2xl font-bold text-white mb-1 text-center">Set a new password</h1>
              <p className="text-sm text-slate-400 mb-6 text-center">
                Choose a new password for your account.
              </p>

              <form onSubmit={handleResetPassword} className="flex flex-col gap-4">
                <PasswordInput
                  id="new-password"
                  label="New password"
                  icon={Lock}
                  placeholder="At least 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
                <PasswordInput
                  id="confirm-password"
                  label="Confirm new password"
                  icon={KeyRound}
                  placeholder="Re-enter your new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />

                {error && <p className="text-xs text-red-400 font-medium text-center">{error}</p>}

                <Button type="submit" variant="primary" size="lg" loading={loading} icon={Lock} className="w-full mt-2">
                  Reset Password
                </Button>
              </form>
            </>
          )}

          {step === 'success' && (
            <div className="flex flex-col items-center text-center py-2">
              <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-4">
                <CheckCircle2 className="w-7 h-7 text-emerald-400" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-1">Password changed</h1>
              <p className="text-sm text-slate-400 mb-6">
                Your password was reset successfully. You can now log in with your new password.
              </p>
              <Button
                variant="primary"
                size="lg"
                className="w-full"
                onClick={() => navigate('/login', { replace: true })}
              >
                Back to Login
              </Button>
            </div>
          )}
        </Card>
      </motion.div>
    </div>
  );
}
