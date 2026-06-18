import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts'
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts'
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables.scss" as *;`
      }
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    css: false,
    testTimeout: 10000,
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/e2e/**',
      '**/playwright.config.ts'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      thresholds: {
        lines: 70,
        functions: 50,
        branches: 60,
        statements: 70
      },
      exclude: [
        'node_modules/',
        'src/**/*.d.ts',
        'src/auto-imports.d.ts',
        'src/components.d.ts',
        'src/main.ts',
        'src/env.d.ts',
        'src/types/**',
        'src/router/**',
        'vite.config.ts',
        'vitest.config.ts',
        'src/__tests__/**',
        'e2e/**',
        'playwright.config.ts'
      ]
    },
    server: {
      deps: {
        inline: ['element-plus']
      }
    }
  }
})
