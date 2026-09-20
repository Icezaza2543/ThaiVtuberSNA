/**
 * Copies ThaiVtuberSNA static assets into web/dist
 * ensuring the deployed GitHub Pages site contains both:
 * 1. index.html (SNA Network Constellation & Research Dashboard)
 * 2. registry.html (Thai Virtual Creator Registry)
 */
const fs = require('fs');
const path = require('path');

const webDir = __dirname;
const distDir = path.join(webDir, 'dist');

if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

const filesToCopy = [
  'index.html',
  'site.css',
  'site.js',
  'design-tokens.css',
  'network.css',
  'network-ui.js',
  'network-state.js',
  'research.css',
  'research.js',
  'data.json',
  'app.js',
];

const dirsToCopy = ['research', 'data'];

for (const file of filesToCopy) {
  const src = path.join(webDir, file);
  const dest = path.join(distDir, file);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
  }
}

for (const dir of dirsToCopy) {
  const srcDir = path.join(webDir, dir);
  const destDir = path.join(distDir, dir);
  if (fs.existsSync(srcDir)) {
    fs.cpSync(srcDir, destDir, { recursive: true });
  }
}

console.log('✓ Successfully copied SNA static assets into web/dist');
