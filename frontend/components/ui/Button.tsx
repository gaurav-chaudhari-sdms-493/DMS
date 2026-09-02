import React from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "primary", size = "md", loading = false, children, disabled, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-background";
    
    const variants = {
      primary: "bg-primary text-white hover:bg-[#0a2449] hover:shadow-[0_0_20px_rgba(13,46,92,0.4)] focus:ring-primary border border-transparent",
      secondary: "bg-surface text-textMain border border-borderDark hover:border-secondary hover:text-secondary hover:shadow-[0_0_20px_rgba(201,162,39,0.35)] focus:ring-secondary",
      ghost: "bg-transparent text-textMuted hover:text-textMain hover:bg-surface focus:ring-borderDark",
      danger: "bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-500/20 hover:shadow-[0_0_20px_rgba(239,68,68,0.3)] focus:ring-red-500",
    };

    const sizes = {
      sm: "h-8 px-3 text-xs",
      md: "h-10 px-4 text-sm",
      lg: "h-12 px-6 text-base",
    };

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${loading || disabled ? "opacity-60 cursor-not-allowed" : ""} ${className}`}
        disabled={loading || disabled}
        {...props}
      >
        {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
