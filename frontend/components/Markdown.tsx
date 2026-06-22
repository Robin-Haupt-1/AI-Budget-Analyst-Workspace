import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders the assistant's narration as markdown (it emits **bold** and bullet
 * lists). Tailwind's preflight strips default list/heading styling, so we
 * restore just what the narration uses via the `components` map — no global
 * typography plugin needed.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-2 list-disc pl-5 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 list-decimal pl-5 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        code: ({ children }) => (
          <code className="rounded bg-gray-200 px-1 py-0.5 text-xs">{children}</code>
        ),
        a: ({ children, href }) => (
          <a href={href} className="text-blue-600 underline" target="_blank" rel="noreferrer">
            {children}
          </a>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
