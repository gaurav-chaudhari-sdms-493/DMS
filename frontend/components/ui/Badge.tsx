import React from "react";

type BadgeStatus = "pending" | "processing" | "indexed" | "failed" | "default";

interface BadgeProps {
  status: BadgeStatus;
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ status, children, className = "" }) => {
  const styles = {
    pending: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    processing: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    indexed: "bg-success/10 text-success border-success/20",
    failed: "bg-red-500/10 text-red-500 border-red-500/20",
    default: "bg-surface text-textMuted border-borderDark",
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status]} ${className}`}>
      {children}
    </span>
  );
};
