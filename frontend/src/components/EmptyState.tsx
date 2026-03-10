import { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`text-center py-12 px-4 ${className}`}>
      {icon && (
        <div className="mx-auto w-16 h-16 mb-4 text-gray-300">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
      {description && (
        <p className="text-gray-500 text-sm max-w-sm mx-auto mb-4">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
}

// Pre-built empty states for common cases
export function EmptyOrders() {
  return (
    <EmptyState
      icon={
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-full h-full">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
      }
      title="No orders yet"
      description="Orders will appear here when customers complete their purchases."
    />
  );
}

export function EmptyBinders() {
  return (
    <EmptyState
      icon={
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-full h-full">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      }
      title="No binders yet"
      description="Complete your home assessment and generate your first binder."
    />
  );
}

export function EmptyUsers() {
  return (
    <EmptyState
      icon={
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-full h-full">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      }
      title="No users yet"
      description="Users will appear here when they sign up."
    />
  );
}

export function EmptySearch({ query }: { query: string }) {
  return (
    <EmptyState
      icon={
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-full h-full">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      }
      title="No results found"
      description={`We couldn't find anything matching "${query}". Try a different search.`}
    />
  );
}
