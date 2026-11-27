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

  await page.emulateMedia({ colorScheme: 'light' });
  await page.locator('button[data-nav=calendar]:visible').click();
  await page.getByRole('button', { name: 'New event' }).click();
  const eventTitle = `Library visit ${engine.name()}`;
  await page.getByLabel('Event title').fill(eventTitle);
  await page.getByLabel('Repeat').selectOption('weekly');
  await page.getByRole('button', { name: 'Save event' }).click();
  await page.getByRole('button', { name: eventTitle, exact: true }).first().waitFor();
  for (const width of [320, 375, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      `${engine.name()} calendar overflow at ${width}px`);
  }
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-calendar-desktop.png`, fullPage: true });
  screenshots.push(`${engine.name()}-calendar-desktop.png`);
  await page.setViewportSize({ width: 390, height: 844 });
  for (const view of ['week', 'day', 'agenda']) {
    const button = page.getByRole('button', { name: view, exact: true });
    await button.click();
    await page.getByRole('button', { name: view, exact: true, pressed: true }).waitFor();
  }
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-agenda.png`, fullPage: true });
  screenshots.push(`${engine.name()}-agenda.png`);
  await page.getByRole('button', { name: new RegExp(eventTitle) }).first().click();
  await page.getByRole('button', { name: 'Skip this occurrence' }).click();
  await page.getByText('Calendar updated.').waitFor();
  await page.locator('button[data-nav=more]:visible').click();
  await page.getByRole('button', { name: /Shopping lists/ }).click();
  await page.getByText('New list', { exact: true }).click();
  const listName = `Weekend market ${engine.name()}`;
  await page.getByLabel('List name').fill(listName);
  await page.getByRole('button', { name: 'Create list' }).click();
  await page.waitForFunction(name => document.querySelector('#shopping-list')?.selectedOptions[0]?.textContent === name, listName);
  await page.getByLabel('Item name').fill('Rolled oats');
  await page.getByLabel('Quantity').fill('2 bags');
  await page.getByLabel('Category').fill('Pantry');
  await page.getByRole('button', { name: 'Add to list' }).click();
  await page.getByRole('button', { name: 'Edit Rolled oats' }).click();
  await page.getByLabel('Quantity').fill('3 bags');
  await page.getByRole('button', { name: 'Save item' }).click();
  await page.getByText('3 bags').waitFor();
  await page.getByRole('button', { name: 'Shopping mode', exact: true }).click();
  for (const width of [320, 375, 390, 430, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
    assert.ok(fits, `${engine.name()} shopping mode overflow at ${width}px`);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-shopping.png`, fullPage: true });
  screenshots.push(`${engine.name()}-shopping.png`);
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  await context.setOffline(true);
  await page.getByRole('button', { name: 'Complete Rolled oats' }).click();
  await page.getByText(/Completion is queued/).waitFor();
  await context.setOffline(false);
  await page.waitForFunction(async () => {
    const id = document.querySelector('#shopping-list')?.value;
    if (!id) return false;
    const response = await fetch(`/api/shopping?list=${encodeURIComponent(id)}`);
    return response.ok && (await response.json()).items.some(item => item.title === 'Rolled oats' && item.completed);
  });

  await context.setOffline(true);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'Sign in' }).waitFor();
  assert.equal(await page.getByText(taskTitle).count(), 0, 'offline reload must not reveal prior member data');
  assert.equal(await page.getByText('Rolled oats').count(), 0, 'offline reload must not reveal shopping data');
  await browser.close();
}

console.log(`Browser flows passed in Chromium and WebKit; screenshots: ${screenshots.join(', ')}`);
