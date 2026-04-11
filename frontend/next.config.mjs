/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Sprint 44 — Bundle optimisation
  // Enable SWC minification (default in Next 14, explicit for clarity)
  swcMinify: true,

  // Webpack config: split large third-party libs into separate chunks
  webpack(config, { isServer }) {
    if (!isServer) {
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          // Recharts is ~500KB — isolate so it only loads on pages that need it
          recharts: {
            name: "recharts",
            test: /[\\/]node_modules[\\/]recharts[\\/]/,
            chunks: "all",
            priority: 20,
          },
          // Lucide icons tree-shakes well but the full set is large
          lucide: {
            name: "lucide",
            test: /[\\/]node_modules[\\/]lucide-react[\\/]/,
            chunks: "all",
            priority: 15,
          },
          // General vendor chunk for remaining node_modules
          vendor: {
            name: "vendor",
            test: /[\\/]node_modules[\\/]/,
            chunks: "all",
            priority: 10,
            reuseExistingChunk: true,
          },
        },
      };
    }
    return config;
  },
};

export default nextConfig;
