import { chromium } from '@playwright/test';
import path from 'path';

async function testInteractiveFlows() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  console.log('--- 1. Testing News Monitor Search and Ingestion Filter ---');
  await page.goto('http://localhost:5173/news', { waitUntil: 'networkidle' });
  const searchInput = page.locator('input[placeholder*="Search headline keywords"]');
  await searchInput.fill('Railway');
  await page.click('button:has-text("Search Coverage")');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.resolve('..', 'docs', 'screenshots', 'interaction_news_search_railway.png') });
  console.log('Captured search interaction.');

  console.log('--- 2. Testing Analyze Article Screening Submission ---');
  await page.goto('http://localhost:5173/analyze', { waitUntil: 'networkidle' });
  await page.click('button:has-text("Load Example Claim")');
  await page.click('button:has-text("Screen Article Content")');
  await page.waitForSelector('text=Model Screening Result', { timeout: 10000 });
  await page.screenshot({ path: path.resolve('..', 'docs', 'screenshots', 'interaction_analyze_submitted.png') });
  console.log('Captured analysis submission result.');

  console.log('--- 3. Testing Evidence & Coverage Graph ---');
  await page.goto('http://localhost:5173/evidence', { waitUntil: 'networkidle' });
  await page.waitForSelector('canvas', { timeout: 10000 });
  await page.screenshot({ path: path.resolve('..', 'docs', 'screenshots', 'interaction_evidence_graph_rendered.png') });
  console.log('Captured evidence coverage graph.');

  await browser.close();
}

testInteractiveFlows();
