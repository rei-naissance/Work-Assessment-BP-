import { sectionTitle, sectionSubtitle } from '../styles/shared';

export default function StepCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="max-w-5xl mx-auto py-2">
      <div className="border-b border-gray-200 pb-2">
        <h2 className={`${sectionTitle} text-base`}>{title}</h2>
        {subtitle && <p className={sectionSubtitle}>{subtitle}</p>}
      </div>
      <div className="pt-4">
        {children}
      </div>
    </section>
  );
}
