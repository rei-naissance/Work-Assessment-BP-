import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../api';
import type { Tier } from '../types';

export default function Checkout() {
  const navigate = useNavigate();
  const location = useLocation();
  const tier: Tier = (location.state as any)?.tier || 'premium';
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');

  const price = tier === 'premium' ? '$99' : '$59';
  const planName = tier === 'premium' ? 'In-Depth Binder' : 'Standard Binder';

  const handlePurchase = async () => {
    setProcessing(true);
    setError('');
    try {
      const res = await api.post('/payments/create-checkout', { tier });
      // Redirect to Stripe Checkout
      window.location.href = res.data.checkout_url;
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      if (detail === 'Payment system not configured' && import.meta.env.DEV) {
        // Dev-only fallback: bypass payment and generate binder directly
        try {
          await api.post('/binders/generate', { tier });
          navigate('/dashboard');
          return;
        } catch (genErr: any) {
          setError(genErr.response?.data?.detail || 'Something went wrong.');
        }
      } else {
        setError(detail || 'Something went wrong. Please try again.');
      }
      setProcessing(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-16 px-4 sm:px-6">
      <div className="max-w-lg mx-auto">
      <div className="bg-white rounded-lg shadow-lg border border-gray-100 overflow-hidden">
        <div className="bg-gradient-to-r from-brand-700 to-brand-800 px-8 py-6">
          <h1 className="font-display text-2xl text-white">Complete Your Purchase</h1>
          <p className="text-brand-200 text-sm mt-1">One-time payment. No subscriptions. Your binder is yours forever.</p>
        </div>

        <div className="px-8 py-6">
          {/* Order summary */}
          <div className="bg-gray-50 rounded-xl p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-navy-900">{planName}</h3>
                <p className="text-xs text-gray-500 mt-0.5">Personalized home operating manual</p>
              </div>
              <span className="text-2xl font-extrabold text-brand-700">{price}</span>
            </div>
            <div className="border-t border-gray-200 pt-3">
              <ul className="space-y-1.5 text-xs text-gray-600">
                <li className="flex items-start gap-2"><span className="text-green-500">&#10003;</span> Professionally formatted PDF</li>
                <li className="flex items-start gap-2"><span className="text-green-500">&#10003;</span> All 8 sections tailored to your home</li>
                <li className="flex items-start gap-2"><span className="text-green-500">&#10003;</span> Update your profile and regenerate anytime</li>
                {tier === 'premium' && (
                  <li className="flex items-start gap-2"><span className="text-green-500">&#10003;</span> AI-personalized content</li>
                )}
              </ul>
            </div>
          </div>

          {/* Secure payment badge */}
          <div className="flex items-center justify-center gap-2 mb-6 text-xs text-gray-400">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
            </svg>
            <span>Secure checkout powered by Stripe</span>
          </div>

          {/* Action */}
          <button
            onClick={handlePurchase}
            disabled={processing}
            className="w-full bg-brand-600 text-white py-3.5 rounded-full font-semibold hover:bg-brand-700 disabled:opacity-50 transition flex items-center justify-center gap-2"
          >
            {processing ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Redirecting to checkout...</span>
              </>
            ) : (
              `Pay ${price}`
            )}
          </button>

          {error && (
            <p className="mt-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}

          <button
            onClick={() => navigate('/select-plan')}
            className="w-full mt-3 text-sm text-gray-500 hover:text-brand-600 transition py-2"
          >
            ← Back to plan selection
          </button>
        </div>
      </div>
      </div>
    </div>
  );
}
