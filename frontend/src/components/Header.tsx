import { useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import api from '../api';
import { useAuth } from '../AuthContext';
import type { Binder } from '../types';
import { btnPrimary } from '../styles/shared';

export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isAdmin, logout: authLogout } = useAuth();
  const isLanding = location.pathname === '/';
  const isLogin = location.pathname === '/login';
  const isDashboard = location.pathname === '/dashboard';
  const isOnboarding = location.pathname === '/onboarding';

  const [binder, setBinder] = useState<Binder | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const showAuthNav = isAuthenticated && !isLanding && !isLogin;

  const fetchBinder = () => {
    if (showAuthNav) {
      api.get('/binders/').then((r) => {
        if (r.data.length > 0) setBinder(r.data[0]);
      }).catch(() => {});
    }
  };

  useEffect(() => {
    fetchBinder();
  }, [showAuthNav]);

  useEffect(() => {
    window.addEventListener('binder:updated', fetchBinder);
    return () => window.removeEventListener('binder:updated', fetchBinder);
  }, [showAuthNav]);

  const logout = async () => {
    await authLogout();
    navigate('/');
  };

  const downloadBinder = async () => {
    if (!binder) return;
    try {
      const res = await api.get(`/binders/${binder.id}/download`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'binderpro.pdf';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      // Silently fail — user can still download from dashboard
    }
  };

  return (
    <header className={`sticky top-0 z-50 ${isLanding ? 'bg-brand-900' : 'bg-white border-b border-gray-200'}`}>
      <div className="flex items-center justify-between px-4 sm:px-6 lg:px-10 py-2">
        {/* Logo — one asset; inverted for contrast on dark (landing) */}
        <div className="flex items-center gap-2">
          {showAuthNav ? (
            <button onClick={() => navigate('/dashboard')} className="flex items-center gap-2">
              <img
                src="/logo.png"
                alt="BinderPro"
                className="h-8 w-auto max-h-10 object-contain object-left"
              />
              {binder && (
                <span className="text-xs text-gray-500 hidden sm:inline">
                  {binder.tier === 'premium' ? 'In-Depth Edition' : 'Standard Edition'}
                </span>
              )}
            </button>
          ) : (
            <button onClick={() => navigate('/')} className="flex items-center">
              <img
                src={isLanding ? '/logo-white.png' : '/logo.png'}
                alt="BinderPro — Your home deserves an operating manual"
                className="h-8 w-auto max-h-10 object-contain object-left"
              />
            </button>
          )}
        </div>

        {/* Nav links + auth */}
        <div className="flex items-center gap-1">
          {/* Landing: logged-out sees Features/Pricing, logged-in sees Dashboard */}
          {isLanding && !isAuthenticated && (
            <>
              <button onClick={() => document.getElementById('whats-included')?.scrollIntoView({ behavior: 'smooth' })} className="hidden sm:inline-block text-sm font-medium text-white/70 hover:text-white px-3 py-1.5 rounded-full transition">Features</button>
              <button onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })} className="hidden sm:inline-block text-sm font-medium text-white/70 hover:text-white px-3 py-1.5 rounded-full transition">Pricing</button>
              <button onClick={() => document.getElementById('faq')?.scrollIntoView({ behavior: 'smooth' })} className="hidden sm:inline-block text-sm font-medium text-white/70 hover:text-white px-3 py-1.5 rounded-full transition">FAQ</button>
            </>
          )}
          {isLanding && isAuthenticated && (
            <button onClick={() => navigate('/dashboard')} className="text-sm font-semibold text-white/90 hover:text-white bg-white/10 border border-white/20 px-4 py-1.5 rounded-full transition hover:bg-white/20">
              Dashboard
            </button>
          )}

          {/* Download button (dashboard only) */}
          {isDashboard && binder?.status === 'ready' && (
            <button
              onClick={downloadBinder}
              className={`${btnPrimary} px-3 sm:px-4 py-1.5 rounded-full flex items-center gap-1.5`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="hidden sm:inline">Download PDF</span>
            </button>
          )}

          {/* Account dropdown */}
          {showAuthNav && (
            <div className="relative ml-1">
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-full hover:bg-gray-100 transition"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="hidden sm:inline">Account</span>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-30" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-100 z-40 py-1">
                    {!isDashboard && !isAdmin && (
                      <button onClick={() => { navigate('/dashboard'); setMenuOpen(false); }} className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                        Dashboard
                      </button>
                    )}
                    {!isAdmin && !isOnboarding && (
                      <button onClick={() => { navigate('/onboarding'); setMenuOpen(false); }} className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                        Edit Profile
                      </button>
                    )}
                    {isAdmin && (
                      <button onClick={() => { navigate('/admin'); setMenuOpen(false); }} className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                        Admin
                      </button>
                    )}
                    <hr className="my-1 border-gray-100" />
                    <button onClick={() => { logout(); setMenuOpen(false); }} className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                      Logout
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Logged-out auth button */}
          {!isAuthenticated && !isLogin && (
            <button onClick={() => navigate('/login')} className={`ml-1 px-5 py-2 rounded-full ${isLanding ? 'text-sm font-semibold bg-white/10 backdrop-blur border border-white/20 text-white hover:bg-white/20 transition' : btnPrimary}`}>
              Log in
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
