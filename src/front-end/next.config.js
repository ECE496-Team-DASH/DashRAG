/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Gzip-compress SSR responses (helpful when not behind a CDN that already compresses)
  compress: true,
  // Don't expose the X-Powered-By: Next.js header
  poweredByHeader: false,
}

module.exports = nextConfig
