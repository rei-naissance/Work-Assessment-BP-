import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { useToast } from './Toast';
import { Icon } from './Icons';

type View = 'menu' | 'report';

export default function HelpBubble() {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<View>('menu');
  const [reportType, setReportType] = useState<'bug' | 'feedback' | 'question'>('bug');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const { showToast } = useToast();

  const close = () => {
    setOpen(false);
    setTimeout(() => {
      setView('menu');
      setMessage('');
    }, 200);
  };

  const submitReport = async () => {
    if (!message.trim()) return;
    setSending(true);
    try {
      await api.post('/feedback', { type: reportType, message, page: window.location.pathname });
      showToast('Feedback sent. Thank you!', 'success');
      close();
    } catch {
      // Fallback: open email if API fails
      const subject = encodeURIComponent(`[BinderPro ${reportType}] Feedback`);
      const body = encodeURIComponent(`Page: ${window.location.pathname}\n\n${message}`);
      window.location.href = `mailto:support@mybinderpro.com?subject=${subject}&body=${body}`;
      close();
    }
    setSending(false);
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Panel */}
      {open && (
        <div className="mb-3 w-80 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden animate-slide-in">
          {view === 'menu' ? (
            <>
              <div className="bg-brand-700 px-5 py-4">
                <p className="text-white font-semibold text-sm">Need help?</p>
                <p className="text-brand-200 text-xs mt-0.5">We're here for you.</p>
              </div>
              <div className="px-4 py-3 space-y-1">
                <button
                  onClick={() => setView('report')}
                  className="w-full flex items-center gap-3 text-sm text-gray-700 hover:bg-gray-50 rounded-lg px-3 py-2.5 transition group text-left"
                >
                  <span className="w-8 h-8 rounded-full bg-amber-50 flex items-center justify-center text-amber-600 group-hover:bg-amber-100 transition flex-shrink-0">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </span>
                  <div>
                    <p className="font-medium">Report an Issue</p>
                    <p className="text-xs text-gray-400">Bug, feedback, or question</p>
                  </div>
                </button>

                <a
                  href="mailto:support@mybinderpro.com"
                  className="w-full flex items-center gap-3 text-sm text-gray-700 hover:bg-gray-50 rounded-lg px-3 py-2.5 transition group"
                >
                  <span className="w-8 h-8 rounded-full bg-brand-50 flex items-center justify-center text-brand-600 group-hover:bg-brand-100 transition flex-shrink-0">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                      <path d="M3 4a2 2 0 00-2 2v1.161l8.441 4.221a1.25 1.25 0 001.118 0L19 7.162V6a2 2 0 00-2-2H3z" />
                      <path d="M19 8.839l-7.77 3.885a2.75 2.75 0 01-2.46 0L1 8.839V14a2 2 0 002 2h14a2 2 0 002-2V8.839z" />
                    </svg>
                  </span>
                  <div>
                    <p className="font-medium">Email Support</p>
                    <p className="text-xs text-gray-400">support@mybinderpro.com</p>
                  </div>
                </a>

                <Link
                  to="/#faq"
                  onClick={close}
                  className="w-full flex items-center gap-3 text-sm text-gray-700 hover:bg-gray-50 rounded-lg px-3 py-2.5 transition group"
                >
                  <span className="w-8 h-8 rounded-full bg-purple-50 flex items-center justify-center text-purple-600 group-hover:bg-purple-100 transition flex-shrink-0">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.94 6.94a.75.75 0 11-1.061-1.061 3 3 0 112.871 5.026v.345a.75.75 0 01-1.5 0v-.5c0-.72.57-1.172 1.081-1.287A1.5 1.5 0 108.94 6.94zM10 15a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                    </svg>
                  </span>
                  <div>
                    <p className="font-medium">FAQs</p>
                    <p className="text-xs text-gray-400">Common questions answered</p>
                  </div>
                </Link>
              </div>
            </>
          ) : (
            <>
              <div className="bg-amber-600 px-5 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white font-semibold text-sm">Report an Issue</p>
                    <p className="text-amber-200 text-xs mt-0.5">Help us improve</p>
                  </div>
                  <button onClick={() => setView('menu')} className="text-white/70 hover:text-white">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="px-4 py-4 space-y-3">
                {/* Type selector */}
                <div className="flex gap-2">
                  {(['bug', 'feedback', 'question'] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setReportType(t)}
                      className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium transition ${
                        reportType === t
                          ? 'bg-amber-100 text-amber-700 border border-amber-300'
                          : 'bg-gray-100 text-gray-600 border border-transparent hover:bg-gray-200'
                      }`}
                    >
                      {t === 'bug' && <><Icon name="bug" className="w-3.5 h-3.5 inline -mt-0.5" /> Bug</>}
                      {t === 'feedback' && <><Icon name="idea" className="w-3.5 h-3.5 inline -mt-0.5" /> Idea</>}
                      {t === 'question' && <><Icon name="help" className="w-3.5 h-3.5 inline -mt-0.5" /> Help</>}
                    </button>
                  ))}
                </div>

                {/* Message */}
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={
                    reportType === 'bug'
                      ? "What went wrong? What did you expect?"
                      : reportType === 'feedback'
                      ? "What would make this better?"
                      : "What do you need help with?"
                  }
                  rows={4}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none"
                />

                <p className="text-xs text-gray-400">
                  Page: {window.location.pathname}
                </p>

                <button
                  onClick={submitReport}
                  disabled={sending || !message.trim()}
                  className="w-full py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50 transition"
                >
                  {sending ? 'Sending...' : 'Send Report'}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setOpen(!open)}
        className={`w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-all ${
          open ? 'bg-gray-700 hover:bg-gray-800' : 'bg-brand-600 hover:bg-brand-700'
        }`}
      >
        {open ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="white" className="w-5 h-5">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="white" className="w-5 h-5">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.94 6.94a.75.75 0 11-1.061-1.061 3 3 0 112.871 5.026v.345a.75.75 0 01-1.5 0v-.5c0-.72.57-1.172 1.081-1.287A1.5 1.5 0 108.94 6.94zM10 15a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
        )}
      </button>
    </div>
  );
}
