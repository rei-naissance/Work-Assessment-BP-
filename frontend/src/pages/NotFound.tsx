import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function NotFound() {
  const { pathname } = useLocation();

  useEffect(() => {
    document.title = 'Page Not Found — BinderPro';
    return () => {
      document.title = "BinderPro — Your Home's Operating Manual";
    };
  }, []);

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-24">
      <div className="max-w-md w-full text-center">
        {/* Number badge */}
        <div className="inline-flex items-center justify-center w-24 h-24 bg-brand-50 rounded-full mb-6">
          <span className="text-4xl font-black text-brand-600" aria-hidden>
            404
          </span>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-3">Page not found</h1>
        <p className="text-gray-500 text-sm mb-2">
          The page{' '}
          <code className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">
            {pathname}
          </code>{' '}
          doesn&apos;t exist.
        </p>
        <p className="text-gray-500 text-sm mb-8">
          It may have been moved, renamed, or you may have followed a broken link.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            <span aria-hidden>←</span> Back to home
          </Link>
          <Link
            to="/support"
            className="inline-flex items-center justify-center px-5 py-2.5 bg-white hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg border border-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300 focus:ring-offset-2"
          >
            Contact support
          </Link>
        </div>
      </div>
    </div>
  );
}
