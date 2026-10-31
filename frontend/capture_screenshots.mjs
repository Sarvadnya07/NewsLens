import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const VIEWPORTS = [
  { name: 'desktop_1920x1080', width: 1920, height: 1080 },
  { name: 'desktop_1440x900', width: 1440, height: 900 },
  { name: 'laptop_1280x800', width: 1280, height: 800 },
  { name: 'tablet_landscape_1024x768', width: 1024, height: 768 },
  { name: 'tablet_portrait_768x1024', width: 768, height: 1024 },
  { name: 'mobile_390x844', width: 390, height: 844 },
  { name: 'small_mobile_360x800', width: 360, height: 800 },
];

const ROUTES = [
  { path: '/', name: 'overview' },
  { path: '/news', name: 'news_monitor' },
  { path: '/analyze', name: 'analyze_article' },
  { path: '/evidence', name: 'evidence_coverage' },
  { path: '/methodology', name: 'methodology' },
];

async function capture() {
  const outputDir = path.resolve('..', 'docs', 'screenshots');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const browser = await chromium.launch();

  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const page = await context.newPage();

    for (const r of ROUTES) {
      try {
        await page.goto(`http://localhost:5173${r.path}`, {
          waitUntil: 'networkidle',
          timeout: 10000,
        });
        const shotPath = path.join(outputDir, `${r.name}_${vp.name}.png`);
        await page.screenshot({ path: shotPath, fullPage: false });
        console.log(`Saved screenshot: ${r.name} @ ${vp.name}`);
      } catch (err) {
        console.error(`Failed ${r.name} @ ${vp.name}:`, err.message);
      }
    }
    await context.close();
  }

  await browser.close();
}

capture();
