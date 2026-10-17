import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Builds to ../frontend_dist so FastAPI serves the compiled app.
// In dev, /api is proxied to the FastAPI server on :8000.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
