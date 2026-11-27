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
  page.on('pageerror', err => console.error(engine.name(), err.message));
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
  const memberPassword = `Child-${crypto.randomUUID()}-Test-Password`;
  const memberUsername = `child-${engine.name()}-${Date.now()}`;
  const ownerSession = await (await page.request.get(`${baseURL}/api/me`)).json();
  const member = await page.request.post(`${baseURL}/api/members`, { data: {
    csrf: ownerSession.csrf, displayName: `Child ${engine.name()}`, role: 'child',
    username: memberUsername, password: memberPassword,
  } });
  assert.equal(member.status(), 201);
  await page.locator('.nav-item[data-nav=tasks]:visible').click();
  await page.getByRole('button', { name: 'New chore' }).click();
  const choreName = `Pack schoolbag ${engine.name()}`;
  await page.getByLabel('Chore name').fill(choreName);
  await page.getByLabel('Repeat').selectOption('daily');
  await page.getByLabel('Routine').selectOption('morning');
  await page.getByLabel(`Child ${engine.name()}`, { exact: true }).check();
  await page.getByLabel('Points', { exact: true }).fill('8');
  await page.getByLabel('Require adult approval').check();
  await page.getByRole('button', { name: 'Save chore' }).click();
  await page.getByRole('heading', { name: 'Chore board' }).waitFor();
  const child = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const childPage = await child.newPage();
  await childPage.goto(baseURL);
  await childPage.getByLabel('Username').fill(memberUsername);
  await childPage.getByLabel('Password').fill(memberPassword);
  await childPage.getByRole('button', { name: 'Sign in' }).click();
  await childPage.locator('.nav-item[data-nav=tasks]:visible').click();
  await childPage.getByRole('button', { name: `Check off ${choreName}` }).click();
  await childPage.getByText('Sent for approval.').waitFor();
  await page.getByRole('button', { name: `Approve chore ${choreName}` }).click();
  await page.getByText('Chore reviewed.').waitFor();
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-chores.png`, fullPage: true });
  screenshots.push(`${engine.name()}-chores.png`);

  for (const tab of [page, childPage]) {
    await tab.locator('button[data-nav=more]:visible').click();
    await tab.locator('button[data-nav=rewards]:visible').click();
  }
  await page.getByRole('button', { name: 'New reward' }).click();
  const rewardName = `Choose a movie ${engine.name()}`;
  await page.getByLabel('Reward name').fill(rewardName);
  await page.getByLabel('Point price').fill('5');
  await page.getByRole('button', { name: 'Save reward' }).click();
  await childPage.getByRole('button', { name: `Request reward ${rewardName}` }).click();
  await childPage.getByText('Reward requested.').waitFor();
  await page.getByRole('button', { name: `Approve reward ${rewardName}` }).click();
  await childPage.getByText('Your balance · 3 points').waitFor();
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-rewards.png`, fullPage: true });
  screenshots.push(`${engine.name()}-rewards.png`);
  await child.close();

  await page.locator('.nav-item[data-nav=meals]:visible').click();
  await page.getByRole('button', { name: 'Recipes', exact: true }).click();
  await page.getByRole('button', { name: 'New recipe' }).click();
  const recipeName = `Oat breakfast ${engine.name()}`;
  await page.getByLabel('Recipe name').fill(recipeName);
  await page.getByLabel('Recipe servings').fill('2');
  await page.getByLabel('Ingredient', { exact: true }).fill(`Breakfast oats ${engine.name()}`);
  await page.getByLabel('Ingredient quantity').fill('1.5');
  await page.getByLabel('Unit', { exact: true }).fill('cups');
  await page.getByLabel('Shopping category').fill('Pantry');
  await page.getByLabel('Instructions').fill('Simmer and serve.');
  await page.getByRole('button', { name: 'Save recipe' }).click();
  await page.getByText(recipeName, { exact: false }).click();
  await page.getByRole('button', { name: 'Plan this recipe' }).click();
  await page.locator('#meal-form select[name=slot]').selectOption('breakfast');
  await page.getByLabel('Servings', { exact: true }).fill('4');
  await page.getByRole('button', { name: 'Save meal' }).click();
  await page.getByRole('heading', { name: 'Meal plan' }).waitFor();
  await page.locator('#grocery-sync-form').getByLabel('Shopping list').selectOption({ label: listName });
  await page.getByRole('button', { name: 'Sync groceries for this week' }).click();
  await page.getByText(/Groceries synced/).waitFor();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-meal-plan.png`, fullPage: true });
  screenshots.push(`${engine.name()}-meal-plan.png`);
  await page.setViewportSize({ width: 390, height: 844 });

  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=shopping]:visible').click();
  await page.getByRole('button', { name: 'Complete Rolled oats' }).waitFor();
  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=inventory]:visible').click();
  await page.getByRole('button', { name: 'New stock item' }).click();
  const stockName = `Yogurt ${engine.name()}`;
  await page.getByLabel('Item name').fill(stockName);
  await page.locator('#inventory-form select[name=location]').selectOption('refrigerator');
  await page.getByLabel('Quantity').fill('2');
  await page.getByLabel('Low-stock threshold').fill('1');
  await page.getByRole('button', { name: 'Save stock item' }).click();
  const stock = page.locator('article').filter({ hasText: stockName });
  await stock.getByText('Adjust stock', { exact: true }).click();
  await stock.getByLabel('Amount').fill('1');
  const [movement] = await Promise.all([
    page.waitForResponse(response => /\/api\/inventory\/[^/]+\/stock$/.test(response.url())),
    stock.getByRole('button', { name: 'Record change' }).click(),
  ]);
  assert.equal(movement.status(), 200, 'inventory stock level should update');
  await stock.getByText('Low stock', { exact: true }).waitFor();
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-inventory.png`, fullPage: true });
  screenshots.push(`${engine.name()}-inventory.png`);
  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=shopping]:visible').click();
  await page.getByRole('button', { name: 'Complete Rolled oats' }).waitFor();
  await page.getByText(`Breakfast oats ${engine.name()}`, { exact: true }).waitFor();
  await page.locator('.shopping-items li').filter({ hasText: `Breakfast oats ${engine.name()}` }).getByText('3 cups', { exact: true }).waitFor();
  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=announcements]:visible').click();
  await page.getByRole('button', { name: 'New announcement' }).click();
  const announcement = `Weekend plans ${engine.name()}`;
  await page.getByLabel('Title', { exact: true }).fill(announcement);
  await page.getByLabel('Message').fill('Meet at the kitchen table.');
  await page.getByLabel('Pin to household display').check();
  await page.getByRole('button', { name: 'Publish announcement' }).click();
  await page.getByRole('heading', { name: announcement }).waitFor();
  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=wall]:visible').click();
  await page.getByRole('heading', { name: 'Pinned announcements' }).waitFor();
  await page.getByText(announcement, { exact: true }).waitFor();
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-wall.png`, fullPage: true });
  screenshots.push(`${engine.name()}-wall.png`);
  await page.getByRole('button', { name: 'Exit display' }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=shopping]:visible').click();
  await page.getByRole('button', { name: 'Complete Rolled oats' }).waitFor();
  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=habits]:visible').click();
  await page.getByRole('button', { name: 'New habit' }).click();
  const habitName = `Read a book ${engine.name()}`;
  await page.getByLabel('Habit name').fill(habitName);
  await page.getByRole('button', { name: 'Save habit' }).click();
  const habit = page.locator('article').filter({ hasText: habitName });
  await habit.getByRole('button', { name: 'Check in today' }).click();
  await habit.getByText('1-day streak').waitFor();

  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=allowance]:visible').click();
  await page.locator('#allowance-form select[name=memberId]').selectOption({ label: `Child ${engine.name()}` });
  await page.getByLabel('Amount in USD').fill('5.50');
  await page.getByLabel('Description').fill(`Weekly allowance ${engine.name()}`);
  await page.getByRole('button', { name: 'Record entry' }).click();
  await page.getByText(`Weekly allowance ${engine.name()}`, { exact: true }).waitFor();
  await page.screenshot({ path: `${artifactDir}/${engine.name()}-allowance.png`, fullPage: true });
  screenshots.push(`${engine.name()}-allowance.png`);

  await page.locator('button[data-nav=more]:visible').click();
  await page.locator('button[data-nav=shopping]:visible').click();
  await page.getByRole('button', { name: 'Complete Rolled oats' }).waitFor();
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
