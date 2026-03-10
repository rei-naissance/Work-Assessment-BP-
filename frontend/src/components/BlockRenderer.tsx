/**
 * Renders Block objects from the backend as React elements for electronic viewing.
 * Mirrors the PDF block types: paragraph, numbered_list, callout_box, table, checklist, subheading, etc.
 */

import DOMPurify from 'dompurify';

interface Block {
  type: string;
  text?: string;
  items?: string[];
  rows?: string[][];
  headers?: string[];
  level?: number;
  ai_generated?: boolean;
}

interface BlockRendererProps {
  blocks: Block[];
}

export default function BlockRenderer({ blocks }: BlockRendererProps) {
  if (!blocks || blocks.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-4">No content available.</p>;
  }

  return (
    <div className="space-y-4">
      {blocks.map((block, idx) => (
        <RenderBlock key={idx} block={block} />
      ))}
    </div>
  );
}

function RenderBlock({ block }: { block: Block }) {
  switch (block.type) {
    case 'heading':
      return <h2 className="text-xl font-bold text-navy-900 mt-4">{block.text}</h2>;

    case 'subheading': {
      const level = block.level || 2;
      if (level >= 3) {
        return (
          <h4 className="text-sm font-semibold text-gray-700 mt-3 mb-1 uppercase tracking-wide">
            {block.text}
          </h4>
        );
      }
      return (
        <h3 className="text-base font-bold text-navy-800 mt-5 mb-2 pb-1 border-b border-gray-100">
          {block.text}
        </h3>
      );
    }

    case 'paragraph':
      return (
        <p className={`text-sm leading-relaxed ${block.ai_generated ? 'text-gray-600 italic' : 'text-gray-700'}`}>
          {block.ai_generated && (
            <span className="inline-block text-[10px] font-semibold text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded mr-2 not-italic">
              Personalized
            </span>
          )}
          <span dangerouslySetInnerHTML={{ __html: formatText(block.text || '') }} />
        </p>
      );

    case 'numbered_list':
      return (
        <ol className="space-y-2 ml-1">
          {(block.items || []).map((item, i) => (
            <li key={i} className="flex gap-3 text-sm text-gray-700">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-50 text-brand-700 flex items-center justify-center text-xs font-bold">
                {i + 1}
              </span>
              <span className="pt-0.5 leading-relaxed" dangerouslySetInnerHTML={{ __html: formatText(item) }} />
            </li>
          ))}
        </ol>
      );

    case 'callout_box':
      return (
        <div className={`rounded-lg px-4 py-3 text-sm border-l-4 ${
          block.ai_generated
            ? 'bg-blue-50 border-blue-300 text-blue-800'
            : 'bg-amber-50 border-amber-300 text-amber-800'
        }`}>
          <span dangerouslySetInnerHTML={{ __html: formatText(block.text || '') }} />
        </div>
      );

    case 'checklist':
      return (
        <ul className="space-y-1.5 ml-1">
          {(block.items || []).map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
              <span className="flex-shrink-0 w-4 h-4 mt-0.5 rounded border border-gray-300 bg-white" />
              <span dangerouslySetInnerHTML={{ __html: formatText(item) }} />
            </li>
          ))}
        </ul>
      );

    case 'table':
      return (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            {block.headers && block.headers.length > 0 && (
              <thead>
                <tr className="bg-navy-800 text-white">
                  {block.headers.map((h, i) => (
                    <th key={i} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {(block.rows || []).map((row, ri) => (
                <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  {row.map((cell, ci) => (
                    <td key={ci} className="px-3 py-2 text-gray-700 border-t border-gray-100">
                      <span dangerouslySetInnerHTML={{ __html: formatText(cell) }} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'spacer':
    case 'page_break':
      return null;

    default:
      // Log unrecognized block types in development
      if (import.meta.env.DEV) {
        console.warn(`Unrecognized block type: ${block.type}`, block);
      }
      return <p className="text-sm text-gray-500">{block.text}</p>;
  }
}

function formatText(text: string): string {
  const html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  return DOMPurify.sanitize(html, { ALLOWED_TAGS: ['strong', 'em', 'br'] });
}
