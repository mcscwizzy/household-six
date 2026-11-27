import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium, webkit } from 'playwright';

const baseURL = process.env.HOUSEHOLD_SIX_URL || 'http://127.0.0.1:3000';
const artifactDir = process.env.PLAYWRIGHT_OUTPUT_DIR || 'artifacts/e2e';
const username = `browser-${Date.now()}`;
const password = `Browser-${crypto.randomUUID()}-Test-Password`;
const screenshots = [];

async function initializeHousehold() {
  const response = await fetch(`${baseURL}/api/setup`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ household: 'Browser Test Home', displayName: 'Browser Owner', username, password }),
  });
  assert.equal(response.status, 200, 'first-run setup should create disposable household');
}

await initializeHousehold();
await mkdir(artifactDir, { recursive: true });

for (const engine of [chromium, webkit]) {
  const browser = await engine.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'allow' });
  const page = await context.newPage();
  await page.goto(baseURL);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.locator('.shell').waitFor();

  await page.getByRole('button', { name: /Add/ }).first().click();
  await page.getByRole('button', { name: 'Task', exact: true }).click();
  const taskTitle = `Browser chore ${engine.name()} ${Date.now()}`;
  await page.getByLabel('Title').fill(taskTitle);
  await page.getByRole('button', { name: 'Save task' }).click();
  await page.getByText(taskTitle).waitFor();
  await page.getByRole('button', { name: `Complete ${taskTitle}` }).click();
  await page.getByRole('button', { name: `Completed ${taskTitle}` }).waitFor();

  for (const width of [320, 375, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    assert.ok(dimensions.content <= dimensions.viewport, `${engine.name()} horizontal overflow at ${width}px: ${JSON.stringify(dimensions)}`);
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-light.png`, fullPage: true });
  screenshots.push(`${engine.name()}-light.png`);
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-dark.png`, fullPage: true });
  screenshots.push(`${engine.name()}-dark.png`);

  await page.evaluate(() => navigator.serviceWorker.ready);
  await context.setOffline(true);
  await page.reload();
  await page.getByRole('button', { name: 'Sign in' }).waitFor();
  assert.equal(await page.getByText(taskTitle).count(), 0, 'offline reload must not reveal prior member data');
  await browser.close();
}

console.log(`Browser flows passed in Chromium and WebKit; screenshots: ${screenshots.join(', ')}`);
