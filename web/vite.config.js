import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  
  // Development server configuration
  server: {
    // In development, proxy /api requests to local FastAPI backend
    // This is only used during `npm run dev`
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
    // Hot module replacement port
    middlewareMode: false,
  },

  // Build configuration
  build: {
    // Output directory
    outDir: "dist",
    
    // Minify for production
    minify: "terser",
    
    // Generate source maps for debugging (optional, disable for smaller bundle)
    sourcemap: false,
    
    // Asset size warnings
    chunkSizeWarningLimit: 500,
    
    // Rollup options for optimization
    rollupOptions: {
      output: {
        // Manual chunks strategy for better caching
        manualChunks: {
          "vendor-react": ["react", "react-dom"],
          "vendor-framer": ["framer-motion"],
          "vendor-three": ["three", "@react-three/fiber", "@react-three/drei"],
        },
      },
    },
  },

  // Environment variables
  // Variables starting with VITE_ are exposed to client code
  // Example: import.meta.env.VITE_API_BASE_URL
  
  // Define globals
  define: {
    __APP_VERSION__: JSON.stringify("1.0.0"),
  },
});

