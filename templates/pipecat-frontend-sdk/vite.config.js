import { defineConfig } from 'vite';

export default defineConfig({
    server: {
        proxy: {
            '/connect': {
                target: 'http://0.0.0.0:8000', // Replace with your backend URL
                changeOrigin: true, 
            },
        },
    },
    build: {
        outDir: "../../static/pipecat-build/", // Output directory
        emptyOutDir: true, // Clean old files before building
        rollupOptions: {
            output: {
                entryFileNames: "bundle.js", // Always output as bundle.js
                assetFileNames: "[name][extname]", // Keep other assets organized
            },
        },
    },
});
