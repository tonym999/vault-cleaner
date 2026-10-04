import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, type Plugin } from 'vitest/config';

// The Flask server to develop against (`python spikes/issue-206/dev.py` sets
// both).  Only `vite dev` reads them; a build contains neither.
const backend = process.env.VC_SPIKE_BACKEND;
const devPort = Number(process.env.VC_SPIKE_DEV_PORT ?? 5173);
const devOrigin = `http://127.0.0.1:${devPort}`;

/**
 * Write the bundler's own list of the modules in each output file, so the
 * licence scan (experiment S12) reads what was built, not a hand-kept list.
 */
function moduleList(): Plugin {
  return {
    name: 'spike-module-list',
    apply: 'build',
    generateBundle(_options, bundle) {
      const outputs: Record<string, string[]> = {};
      const css = new Set<string>();
      for (const [fileName, chunk] of Object.entries(bundle)) {
        if (chunk.type !== 'chunk') continue;
        outputs[fileName] = Object.entries(chunk.modules)
          .filter(([, module]) => module.renderedLength > 0)
          .map(([id]) => id);
        for (const id of chunk.moduleIds) if (/\.css($|\?)/.test(id)) css.add(id);
      }
      this.emitFile({
        type: 'asset',
        fileName: 'modules.json',
        source: JSON.stringify({ outputs, css: [...css] }, null, 2),
      });
    },
  };
}

export default defineConfig({
  // Relative URLs, so the same build works at /spike/ and at /.
  base: './',
  plugins: [tailwindcss(), svelte(), moduleList()],
  build: {
    // No data: URIs: the server's policy has no img-src or font-src.
    assetsInlineLimit: 0,
    // Browsers that support `light-dark()` natively.  With Vite's default
    // target, lightningcss (MPL-2.0, build-time only) lowers daisyUI's colour
    // schemes and writes `--lightningcss-light` / `--lightningcss-dark`
    // helper properties into the stylesheet.  With this target it writes
    // nothing of its own (experiment S12 checks the output for traces).
    cssTarget: ['chrome123', 'firefox120', 'safari17.5'],
    modulePreload: { polyfill: false },
    rolldownOptions: {
      output: {
        // Stable names: Flask serves a fixed allow-list, and every response
        // is no-store, so a content hash would buy nothing.
        entryFileNames: 'assets/app.js',
        assetFileNames: 'assets/app[extname]',
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: devPort,
    strictPort: true,
    // Development only.  The Flask server accepts requests whose Host and
    // Origin are its own.  The proxy presents the backend's Host, and
    // rewrites Origin only when it is exactly this dev server's own origin;
    // any other Origin is forwarded untouched and Flask refuses it.
    proxy: backend
      ? Object.fromEntries(
          ['/api', '/bootstrap'].map((path) => [
            path,
            {
              target: backend,
              changeOrigin: true,
              configure(proxy) {
                proxy.on('proxyReq', (request) => {
                  if (request.getHeader('origin') === devOrigin) request.setHeader('origin', backend);
                });
              },
            },
          ]),
        )
      : undefined,
  },
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
});
