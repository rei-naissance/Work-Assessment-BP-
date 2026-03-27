import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { getErrorMessage } from '../api';
import { useAuth } from '../AuthContext';
import { card, btnPrimary, pageTitle } from '../styles/shared';
import { Icon } from '../components/Icons';

const STEPS_PREVIEW = [
  { iconName: 'home', text: 'Tell us about your home — type, location, and systems' },
  { iconName: 'family', text: 'Add your household, contacts, and service providers' },
  { iconName: 'checklist', text: 'Set your preferences for maintenance style and priorities' },
  { iconName: 'document', text: 'Receive a custom binder built around how you want things to run' },
];

const DEV_ACCOUNTS = [
  { email: 'admin@test.com', label: 'Admin', description: 'Full admin access + dashboard' },
  { email: 'user@test.com', label: 'User', description: 'Standard user account' },
];

export default function Login() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'email' | 'otp'>('email');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const requestOtp = async () => {
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/request-otp', { email });
      setStep('otp');
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/auth/verify-otp', { email, code });
      login(res.data.access_token);
      // Route based on whether user already has a binder
      try {
        const binders = await api.get('/binders/');
        if (binders.data.length > 0) {
          navigate('/dashboard');
        } else {
          navigate('/onboarding');
        }
      } catch {
        navigate('/onboarding');
      }
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const devLogin = async (devEmail: string) => {
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/auth/dev-login', { email: devEmail });
      login(res.data.access_token);
      const { is_admin } = JSON.parse(atob(res.data.access_token.split('.')[1]));
      navigate(is_admin ? '/admin' : '/dashboard');
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center py-12 px-4 sm:px-6">
      <div className="w-full max-w-5xl grid lg:grid-cols-2 gap-10 items-center">

        {/* Left: welcome messaging */}
        <div>
          <h1 className={`${pageTitle} text-3xl mb-3`}>
            Let's get your home organized.
          </h1>
          <p className="text-gray-500 leading-relaxed mb-8">
            You're about to build a personalized operating manual for your home — everything
            from emergency procedures to maintenance schedules to who to call when something
            breaks. It starts with a few simple questions about your home and how you want
            things to run.
          </p>

          <div className="space-y-4">
            {STEPS_PREVIEW.map((s) => (
              <div key={s.text} className="flex items-start gap-3">
                <span className="w-9 h-9 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center flex-shrink-0">
                  <Icon name={s.iconName} className="w-4.5 h-4.5" />
                </span>
                <p className="text-sm text-gray-600 leading-relaxed pt-1.5">{s.text}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 pt-6 border-t border-gray-100">
            <p className="text-xs text-gray-400 leading-relaxed">
              Free to set up. No password needed. Pay only when you generate your binder.
            </p>
          </div>
        </div>

        {/* Right: login card */}
        <div className="space-y-4">
          <div className={`${card} rounded-lg overflow-hidden`}>
            <div className="bg-gradient-to-r from-brand-700 to-brand-800 px-8 py-6">
              <h2 className="font-display text-2xl text-white">
                {step === 'email' ? 'Get Started' : 'Check your inbox'}
              </h2>
              <p className="text-brand-200 text-sm mt-1">
                {step === 'email' ? (
                  "Enter your email and we'll send you a secure code."
                ) : email ? (
                  <>We sent a 6-digit code to <strong className="text-white">{email}</strong>.</>
                ) : (
                  'Enter your email and the code we sent you.'
                )}
              </p>
            </div>

            <div className="px-8 py-6">
              {step === 'email' && (
                <>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Email address
                  </label>
                  <input
                    type="email"
                    className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    onKeyDown={(e) => e.key === 'Enter' && email && requestOtp()}
                  />
                  <button
                    onClick={requestOtp}
                    disabled={loading || !email}
                    className={`w-full mt-4 py-2.5 rounded-full ${btnPrimary}`}
                  >
                    {loading ? 'Sending...' : 'Continue'}
                  </button>
                  <button
                    onClick={() => setStep('otp')}
                    className="w-full mt-2 text-sm text-gray-500 hover:text-brand-600 transition"
                  >
                    Already have a code?
                  </button>
                </>
              )}

              {step === 'otp' && (
                <>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Email address
                  </label>
                  <input
                    type="email"
                    className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition mb-4"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                  />
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Verification code
                  </label>
                  <input
                    type="text"
                    className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm tracking-widest text-center font-mono focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                    maxLength={6}
                    placeholder="000000"
                    onKeyDown={(e) => e.key === 'Enter' && code.length === 6 && verifyOtp()}
                  />
                  <button
                    onClick={verifyOtp}
                    disabled={loading || code.length !== 6}
                    className={`w-full mt-4 py-2.5 rounded-full ${btnPrimary}`}
                  >
                    {loading ? 'Verifying...' : 'Log in'}
                  </button>
                  <button
                    onClick={() => { setStep('email'); setCode(''); setError(''); }}
                    className="w-full mt-2 text-sm text-gray-500 hover:text-brand-600 transition"
                  >
                    Use a different email
                  </button>
                </>
              )}

              {error && (
                <p className="mt-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}
            </div>
          </div>

          {/* Dev test accounts — only in development */}
          {import.meta.env.DEV && (
            <div className="border border-dashed border-amber-300 bg-amber-50/50 rounded-xl p-4">
              <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-3">Dev Accounts</p>
              <div className="flex gap-2">
                {DEV_ACCOUNTS.map((acct) => (
                  <button
                    key={acct.email}
                    onClick={() => devLogin(acct.email)}
                    disabled={loading}
                    className="flex-1 text-left px-3 py-2.5 bg-white border border-amber-200 rounded-lg hover:border-amber-400 hover:bg-amber-50 transition disabled:opacity-50"
                  >
                    <p className="text-sm font-medium text-gray-800">{acct.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{acct.description}</p>
                    <p className="text-xs text-amber-600 font-mono mt-1">{acct.email}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
