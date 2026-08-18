/** @type {import('next').NextConfig} */
const isDesktopBuild = process.env.BUILD_TARGET === 'desktop' || Boolean(process.env.TAURI_ENV);

const nextConfig = {
  ...(isDesktopBuild
    ? {
        output: 'export',
        trailingSlash: true,
      }
    : {}),
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig;


