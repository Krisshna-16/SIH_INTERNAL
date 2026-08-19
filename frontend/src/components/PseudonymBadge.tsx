import React from 'react';

interface PseudonymBadgeProps {
  token: string;
}

export const PseudonymBadge: React.FC<PseudonymBadgeProps> = ({ token }) => {
  return (
    <span className="pseudonym-badge" title="Identity pseudonymized by Privacy Gateway prior to LLM dispatch">
      🔒 {token}
    </span>
  );
};
