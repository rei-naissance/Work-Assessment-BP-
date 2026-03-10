import { useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function Terms() {
  useEffect(() => {
    document.title = 'Terms of Service — BinderPro';
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
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Terms of Service</h1>

      <div className="prose prose-gray max-w-none">
        <p className="text-gray-600 mb-6">
          <em>Last updated: January 29, 2026</em>
        </p>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Acceptance of Terms</h2>
          <p className="text-gray-700">
            By accessing or using BinderPro, you agree to be bound by these Terms of Service.
            If you do not agree to these terms, please do not use our service.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">2. Description of Service</h2>
          <p className="text-gray-700">
            BinderPro is a service that generates personalized home management guides based on
            information you provide about your home. The service includes:
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2 mt-4">
            <li>A personalized PDF home operating manual</li>
            <li>Emergency quick-reference cards</li>
            <li>Maintenance schedules and checklists</li>
            <li>Contact organization tools</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">3. User Responsibilities</h2>
          <p className="text-gray-700 mb-4">You agree to:</p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2">
            <li>Provide accurate information about your home</li>
            <li>Keep your account credentials secure</li>
            <li>Not use the service for any unlawful purpose</li>
            <li>Not attempt to access other users' accounts or data</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Payment Terms</h2>
          <p className="text-gray-700 mb-4">
            BinderPro is a one-time purchase. Payment is processed securely through Stripe.
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2">
            <li>Prices are listed in US dollars</li>
            <li>Payment is due at time of purchase</li>
            <li>You will receive email confirmation upon successful payment</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Refund Policy</h2>
          <p className="text-gray-700 mb-4">
            We want you to be satisfied with your BinderPro. If you're not happy with your purchase:
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2">
            <li>Request a refund within 30 days of purchase</li>
            <li>Refunds are processed within 5-10 business days</li>
            <li>Contact support@mybinderpro.com with your order details</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Limitation of Liability</h2>
          <p className="text-gray-700">
            BinderPro provides general home management guidance. We are not responsible for:
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-2 mt-4">
            <li>Accuracy of information you provide</li>
            <li>Damage resulting from following general maintenance guides</li>
            <li>Third-party service provider quality or availability</li>
            <li>Emergency situations - always call 911 for emergencies</li>
          </ul>
          <p className="text-gray-700 mt-4">
            The content provided is for informational purposes only and should not replace
            professional advice from licensed contractors, electricians, plumbers, or other specialists.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">7. Intellectual Property</h2>
          <p className="text-gray-700">
            The BinderPro service, including all content, features, and functionality, is owned
            by BinderPro and protected by copyright, trademark, and other intellectual property laws.
            Your generated binder is for personal use only.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">8. Termination</h2>
          <p className="text-gray-700">
            We reserve the right to terminate or suspend access to our service immediately,
            without prior notice, for conduct that we believe violates these Terms or is
            harmful to other users or us.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">9. Changes to Terms</h2>
          <p className="text-gray-700">
            We may update these Terms from time to time. We will notify you of significant changes
            via email or through the service. Continued use after changes constitutes acceptance
            of the new terms.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">10. Contact Us</h2>
          <p className="text-gray-700">
            If you have questions about these Terms, please contact us at:
            <br />
            <a href="mailto:support@mybinderpro.com" className="text-brand-600 hover:text-brand-700 hover:underline focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded">
              support@mybinderpro.com
            </a>
          </p>
        </section>
      </div>
    </div>
  );
}
