import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@scenes': path.resolve(__dirname, './src/scenes'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@lib': path.resolve(__dirname, './src/lib'),
      '@assets': path.resolve(__dirname, './src/assets'),
      '@styles': path.resolve(__dirname, './src/styles'),
      '@types': path.resolve(__dirname, './src/types'),
    },
  },
  server: {
    port: 5173,
    strictPort: false, // Allow Vite to find another port if 5173 is busy
    host: '0.0.0.0', // Allow external connections for mobile testing
    watch: {
      ignored: ['**/backend/**', '**/.venv/**', '**/node_modules/**'] // Exclude backend and Python venv from file watching
    },
    // Proxy only for local development - removed for production deployment
    ...(process.env.NODE_ENV !== 'production' && {
      proxy: {
        '/api': {
          target: 'http://localhost:8002',
          changeOrigin: true,
          configure: (_proxy, _options) => {
            // Updated to match current backend port (8002)
          }
        },
      }
    }),
    allowedHosts: true
  },
  build: {
    // Mobile performance optimizations
    target: 'es2015',
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          // Split large libraries for better mobile loading
          'framer-motion': ['framer-motion'],
          'three': ['three', '@react-three/fiber', '@react-three/drei']
        }
      }
    }
  },
})