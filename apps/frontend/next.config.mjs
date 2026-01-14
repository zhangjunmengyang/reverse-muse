/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    // Ignore canvas module for PDF.js (not needed in browser)
    config.resolve.alias.canvas = false;
    config.resolve.alias.encoding = false;

    // Fix for pdfjs-dist ESM issues with webpack
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
        stream: false,
        zlib: false,
      };
    }

    return config;
  },
  // Transpile pdfjs-dist for better compatibility
  transpilePackages: ['pdfjs-dist'],

  // Experimental settings for ESM support
  experimental: {
    esmExternals: 'loose',
  },
};

export default nextConfig;
