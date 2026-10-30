import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';
await mkdir('static/fonts', { recursive: true });
for (const [source, destination] of [
  ['@fontsource-variable/dm-sans/files/dm-sans-latin-wght-normal.woff2', 'dm-sans-latin.woff2'],
  ['@fontsource-variable/fraunces/files/fraunces-latin-wght-normal.woff2', 'fraunces-latin.woff2'],
  ['@fontsource-variable/fraunces/files/fraunces-latin-wght-italic.woff2', 'fraunces-latin-italic.woff2'],
  ['@fontsource-variable/dm-sans/LICENSE', 'DM-Sans-LICENSE.txt'],
  ['@fontsource-variable/fraunces/LICENSE', 'Fraunces-LICENSE.txt'],
  ['@fontsource/bebas-neue/files/bebas-neue-latin-400-normal.woff2', 'bebas-neue-latin.woff2'],
  ['@fontsource/bebas-neue/LICENSE', 'Bebas-Neue-LICENSE.txt'],
]) await copyFile(`node_modules/${source}`, `static/fonts/${destination}`);
await build({
  entryPoints: ['static/js/food-studio.mjs'],
  outfile: 'static/vendor/food-studio.mjs',
  bundle: true, format: 'esm', platform: 'browser', target: 'es2022',
  minify: true, legalComments: 'eof',
});
await build({
  entryPoints: ['static/css/food-experience.css'],
  outfile: 'static/vendor/food-experience.css',
  bundle: true, minify: true, legalComments: 'eof',
  plugins: [{ name: 'public-asset-urls', setup(builder) {
    builder.onResolve({ filter: /^\/static\// }, args => ({ path: args.path, external: true }));
  } }],
});
