import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';

type Status = 'verifying' | 'generating' | 'complete' | 'error';

export default function PaymentSuccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [status, setStatus] = useState<Status>('verifying');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!sessionId) {
      navigate('/dashboard');
      return;
    }

    const processPayment = async () => {
      try {
        // Verify the payment with our backend
        const verifyRes = await api.get(`/payments/verify-session/${sessionId}`);

        if (verifyRes.data.status === 'paid') {
          setStatus('generating');

          // Generate the binder
          const tier = verifyRes.data.tier || 'premium';
          await api.post('/binders/generate', { tier });

          setStatus('complete');

          // Redirect to dashboard after a moment
          setTimeout(() => {
            navigate('/dashboard');
          }, 2000);
        } else {
          setError('Payment was not completed. Please try again.');
          setStatus('error');
        }
      } catch (e: any) {
        setError(e.response?.data?.detail || 'Something went wrong processing your payment.');
        setStatus('error');
      }
    };

    processPayment();
  }, [sessionId, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6">
      <div className="max-w-5xl mx-auto w-full flex justify-center">
        <div className="max-w-md w-full text-center">
        {status === 'verifying' && (
          <>
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-brand-100 flex items-center justify-center">
              <svg className="animate-spin h-8 w-8 text-brand-600" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
            <h1 className="font-display text-2xl text-navy-900 mb-2">Verifying Payment...</h1>
            <p className="text-gray-500">Please wait while we confirm your purchase.</p>
          </>
        )}

        {status === 'generating' && (
          <>
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-brand-100 flex items-center justify-center">
              <svg className="animate-spin h-8 w-8 text-brand-600" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
            <h1 className="font-display text-2xl text-navy-900 mb-2">Payment Confirmed!</h1>
            <p className="text-gray-500 mb-4">Now generating your personalized binder...</p>
            <div className="bg-gray-100 rounded-full h-2 overflow-hidden">
              <div className="bg-brand-600 h-full animate-pulse" style={{ width: '60%' }} />
            </div>
          </>
        )}

        {status === 'complete' && (
          <>
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-green-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="font-display text-2xl text-navy-900 mb-2">Your Binder is Ready!</h1>
            <p className="text-gray-500 mb-6">Redirecting you to your dashboard...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="font-display text-2xl text-navy-900 mb-2">Something Went Wrong</h1>
            <p className="text-gray-500 mb-6">{error}</p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => navigate('/checkout')}
                className="px-6 py-2.5 bg-brand-600 text-white rounded-full font-semibold hover:bg-brand-700 transition"
              >
                Try Again
              </button>
              <button
                onClick={() => navigate('/dashboard')}
                className="px-6 py-2.5 border border-gray-200 text-gray-600 rounded-full font-semibold hover:bg-gray-50 transition"
              >
                Go to Dashboard
              </button>
            </div>
          </>
        )}
        </div>
      </div>
    </div>
  );
}
