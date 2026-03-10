import { useLocation } from 'react-router-dom';
import { useEffect } from 'react';

/**
 * Scroll to top on route (pathname) change, and scroll to the element
 * matching location.hash when present (e.g. /#faq).
 */
export default function ScrollManager() {
  const location = useLocation();

  // Scroll to top when pathname changes (e.g. navigating to a new page).
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  // When there's a hash (e.g. /#faq), scroll the target element into view after the route has rendered.
  useEffect(() => {
    const hash = location.hash;
    if (!hash) return;
    const id = hash.slice(1);
    const el = document.getElementById(id);
    if (el) {
      // Small delay so the target section is in the DOM (e.g. Landing FAQ).
      const t = setTimeout(() => {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 50);
      return () => clearTimeout(t);
    }
  }, [location.pathname, location.hash]);

  return null;
}
