import Link from "next/link";
import React from "react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen text-center px-4 bg-gdriveBg text-gdriveTextMain">
      <div className="flex justify-center mb-6">
        <img src="/stark-dms-app-logo.svg" alt="App Logo" className="h-20 w-auto object-contain" />
      </div>
      <h1 className="text-4xl font-extrabold mb-2">404 - Page Not Found</h1>
      <p className="text-textMuted mb-6">The page you are looking for does not exist or has been moved.</p>
      <Link
        href="/drive"
        className="px-6 py-2.5 bg-primary text-white font-medium rounded-lg shadow-md hover:bg-primary/90 transition-all"
      >
        Back to Drive
      </Link>
    </div>
  );
}
