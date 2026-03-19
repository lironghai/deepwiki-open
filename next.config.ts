import type { NextConfig } from "next";

const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';
const WS_SERVER_BASE_URL = process.env.WS_SERVER_BASE_URL || 'http://localhost:29004';
// GitNexus 内网地址，由 Next 转发，无需对外暴露 3001 端口
const GITNEXUS_UPSTREAM = process.env.GITNEXUS_UPSTREAM_URL || 'http://127.0.0.1:3001';

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  // 将服务器 URL 暴露给客户端（浏览器）
  env: {
    NEXT_PUBLIC_WS_SERVER_URL: WS_SERVER_BASE_URL,
    NEXT_PUBLIC_GITNEXUS_DEFAULT_OPENAI_API_KEY:
      process.env.DASHSCOPE_API_KEY || process.env.OPENAI_API_KEY || '',
    NEXT_PUBLIC_GITNEXUS_DEFAULT_OPENAI_BASE_URL:
      process.env.DASHSCOPE_BASE_URL || process.env.OPENAI_BASE_URL || '',
    NEXT_PUBLIC_GITNEXUS_DEFAULT_OPENAI_MODEL:
      process.env.GITNEXUS_DEFAULT_OPENAI_MODEL || 'qwen-plus',
  },
  // Disable linting during build to speed up deployment
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Disable TypeScript errors during build
  typescript: {
    ignoreBuildErrors: true,
  },
  // Optimize build for Docker
  experimental: {
    optimizePackageImports: ['@mermaid-js/mermaid', 'react-syntax-highlighter', 'reactflow'],
  },
  // Reduce memory usage during build
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    }
    // Optimize bundle size
    config.optimization = {
      ...config.optimization,
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
          },
          // 单独打包reactflow以避免chunk加载问题
          reactflow: {
            test: /[\\/]node_modules[\\/]reactflow[\\/]/,
            name: 'reactflow',
            chunks: 'all',
            priority: 20,
          },
        },
      },
    };
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/wiki_cache/:path*',
        destination: `${TARGET_SERVER_BASE_URL}/api/wiki_cache/:path*`,
      },
      {
        source: '/export/wiki/:path*',
        destination: `${TARGET_SERVER_BASE_URL}/export/wiki/:path*`,
      },
      {
        source: '/api/wiki_cache',
        destination: `${TARGET_SERVER_BASE_URL}/api/wiki_cache`,
      },
      {
        source: '/local_repo/structure',
        destination: `${TARGET_SERVER_BASE_URL}/local_repo/structure`,
      },
      {
        source: '/api/auth/status',
        destination: `${TARGET_SERVER_BASE_URL}/auth/status`,
      },
      {
        source: '/api/auth/validate',
        destination: `${TARGET_SERVER_BASE_URL}/auth/validate`,
      },
      {
        source: '/api/lang/config',
        destination: `${TARGET_SERVER_BASE_URL}/lang/config`,
      },
      {
        source: '/api/codemap/:path*',
        destination: `${TARGET_SERVER_BASE_URL}/api/codemap/:path*`,
      },
      {
        source: '/api/project',
        destination: `${TARGET_SERVER_BASE_URL}/api/project`,
      },
      // GitNexus 深度图谱：同源访问 /gitnexus，由 Next 转发到本地 3001，Docker 无需单独映射 3001
      {
        source: '/gitnexus',
        destination: `${GITNEXUS_UPSTREAM}`,
      },
      {
        source: '/gitnexus/:path*',
        destination: `${GITNEXUS_UPSTREAM}/:path*`,
      },
    ];
  },
};

export default nextConfig;
