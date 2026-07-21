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
        className={`rounded-xl p-6 transition-all duration-300 ${gradient ? "border border-transparent bg-[linear-gradient(var(--bg),var(--bg))_padding-box,linear-gradient(to_bottom_right,var(--primary),var(--secondary))_border-box]" : "glass"} ${glow ? "hover:shadow-[0_0_30px_rgba(99,102,241,0.25)] hover:-translate-y-1 hover:border-primary/50" : ""} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = "Card";
