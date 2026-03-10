import { useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function Support() {
  useEffect(() => {
    document.title = 'Support — BinderPro';
    return () => { document.title = 'BinderPro — Your Home\'s Operating Manual'; };
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium mb-8 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded"
      >
        <span aria-hidden>←</span> Back to home
      </Link>
      <h1 className="text-3xl font-bold text-gray-900 mb-4">Support</h1>
      <p className="text-gray-600 mb-8">
        Have a question, ran into an issue, or want to suggest an improvement? We're here to help.
      </p>

      <div className="space-y-6">
        <section className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Email us</h2>
          <p className="text-sm text-gray-600 mb-4">
            For account issues, billing, or general questions, email our support team. We typically respond within 1–2 business days.
          </p>
          <a
            href="mailto:support@mybinderpro.com"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-brand-600 text-white text-sm font-semibold rounded-lg hover:bg-brand-700 transition focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M3 4a2 2 0 00-2 2v1.161l8.441 4.221a1.25 1.25 0 001.118 0L19 7.162V6a2 2 0 00-2-2H3z" />
              <path d="M19 8.839l-7.77 3.885a2.75 2.75 0 01-2.46 0L1 8.839V14a2 2 0 002 2h14a2 2 0 002-2V8.839z" />
            </svg>
            support@mybinderpro.com
          </a>
        </section>

        <section className="bg-gray-50 rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">FAQs</h2>
          <p className="text-sm text-gray-600 mb-4">
            Many common questions are answered on our home page.
          </p>
          <Link
            to="/#faq"
            className="inline-flex items-center gap-2 text-sm font-medium text-brand-600 hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded"
          >
            View FAQs on home page
            <span aria-hidden>→</span>
          </Link>
        </section>
      </div>
    </div>
  );
}
