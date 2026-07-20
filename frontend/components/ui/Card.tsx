import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: boolean;
  gradient?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = "", glow = false, gradient = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`glass rounded-xl p-6 transition-all duration-300 ${glow ? "hover:shadow-[0_0_20px_rgba(99,102,241,0.2)] hover:-translate-y-1" : ""} ${gradient ? "relative overflow-hidden before:absolute before:inset-0 before:p-[1px] before:bg-gradient-to-br before:from-primary before:to-secondary before:-z-10 before:rounded-xl" : ""} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = "Card";
