import {defineConfig} from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';
import {fileURLToPath} from 'url';

export default defineConfig({
    base: './',
    plugins: [vue()],
    css: {
        postcss: {
            plugins: [
                tailwindcss({
                    config: 'tailwind.config.js',
                }),
                autoprefixer,
            ],
        },
    },
    build: {
        chunkSizeWarningLimit: 1000, // Increase the limit to 1000 kB (1MB)
    },
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    }
});