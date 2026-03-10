import { useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function Privacy() {
  useEffect(() => {
    document.title = 'Privacy Policy — BinderPro';
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
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Privacy Policy</h1>

      <div className="prose prose-gray max-w-none">
        <p className="text-gray-600 mb-6">
          <em>Last updated: January 29, 2026</em>
        </p>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Information We Collect</h2>
          <p className="text-gray-700 mb-4">
            BinderPro collects information you provide directly, including:
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2">
            <li>Account information (email address)</li>
            <li>Home profile data (address, home type, features, systems)</li>
            <li>Contact information (emergency contacts, service providers)</li>
            <li>Payment information (processed securely via Stripe)</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">2. How We Use Your Information</h2>
          <p className="text-gray-700 mb-4">We use the information we collect to:</p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2">
            <li>Generate your personalized BinderPro</li>
            <li>Process payments and provide customer support</li>
            <li>Send transactional emails (receipts, binder notifications)</li>
            <li>Improve our services and user experience</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">3. Data Security</h2>
          <p className="text-gray-700 mb-4">
            We implement industry-standard security measures to protect your data:
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2">
            <li>All data transmitted over HTTPS encryption</li>
            <li>Payment data processed via PCI-compliant Stripe</li>
            <li>Database access restricted and monitored</li>
            <li>Regular security audits and updates</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Data Sharing</h2>
          <p className="text-gray-700 mb-4">
            We do not sell your personal information. We may share data with:
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2">
            <li>Payment processors (Stripe) for transaction processing</li>
            <li>Email service providers for transactional emails</li>
            <li>Law enforcement when required by law</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Your Rights</h2>
          <p className="text-gray-700 mb-4">You have the right to:</p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2">
            <li>Access your personal data</li>
            <li>Request correction of inaccurate data</li>
            <li>Request deletion of your data</li>
            <li>Export your data in a portable format</li>
          </ul>
          <p className="text-gray-700 mt-4">
            To exercise these rights, contact us at privacy@mybinderpro.com
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Data Retention</h2>
          <p className="text-gray-700">
            We retain your data for as long as your account is active. After account deletion,
            we may retain certain data for legal and business purposes for up to 7 years.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">7. Contact Us</h2>
          <p className="text-gray-700">
            If you have questions about this Privacy Policy, please contact us at:
            <br />
            <a href="mailto:privacy@mybinderpro.com" className="text-brand-600 hover:text-brand-700 hover:underline focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded">
              privacy@mybinderpro.com
            </a>
          </p>
        </section>
      </div>
    </div>
  );
}
