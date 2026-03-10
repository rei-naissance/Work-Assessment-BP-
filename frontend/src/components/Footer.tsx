import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="bg-navy-900 py-5">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
        <span className="text-sm text-gray-400">BinderPro &copy; {new Date().getFullYear()}</span>
        <nav className="flex items-center gap-6" aria-label="Footer links">
          <Link
            to="/support"
            className="text-sm text-gray-400 hover:text-white transition focus:outline-none focus:ring-2 focus:ring-white/50 focus:ring-offset-2 focus:ring-offset-navy-900 rounded"
          >
            Support
          </Link>
          <Link
            to="/privacy"
            className="text-sm text-gray-400 hover:text-white transition focus:outline-none focus:ring-2 focus:ring-white/50 focus:ring-offset-2 focus:ring-offset-navy-900 rounded"
          >
            Privacy
          </Link>
          <Link
            to="/terms"
            className="text-sm text-gray-400 hover:text-white transition focus:outline-none focus:ring-2 focus:ring-white/50 focus:ring-offset-2 focus:ring-offset-navy-900 rounded"
          >
            Terms
          </Link>
        </nav>
      </div>
    </footer>
  );
}
