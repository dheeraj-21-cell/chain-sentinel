import React, { useState } from 'react';

interface CopyButtonProps {
  text: string;
  title?: string;
  className?: string;
}

export const CopyButton: React.FC<CopyButtonProps> = ({ text, title = 'Copy to clipboard', className = '' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <button
      onClick={handleCopy}
      className={`copy-btn ${className}`}
      title={copied ? 'Copied!' : title}
      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
    >
      {copied ? (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      ) : (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      )}
    </button>
  );
};
