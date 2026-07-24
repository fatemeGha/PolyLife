import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  server: {
    port: 5178,
    proxy: {
      "/api": {
        target: "http://localhost:9108",
        changeOrigin: true,
      },
    },
  },
});
