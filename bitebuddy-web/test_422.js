const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Listen to network responses
  page.on('response', async (response) => {
    if (response.url().includes('/scan/food/confirm')) {
      console.log('Status:', response.status());
      try {
        console.log('Response:', await response.text());
      } catch (e) {
        console.log('Could not read response');
      }
    }
  });

  // Login first since it needs a session
  await page.goto('http://localhost:3001');
  
  // Wait for login page
  await page.fill('input[type="email"]', 'anak@test.com');
  await page.fill('input[type="password"]', 'password123');
  await page.click('button:has-text("Login")');

  // Wait for navigation to /child
  await page.waitForURL('http://localhost:3001/child');
  
  // Go to analysis page
  await page.goto('http://localhost:3001/child/analysis?imageUri=null&ingredients=%5B%7B%22ingredient%22%3A%22Apple%22%2C%22weight_g%22%3A1%2C%22fdcId%22%3Anull%7D%5D');
  
  // Wait for it to load
  await page.waitForTimeout(2000);
  
  // Click Confirm button
  await page.click('button:has-text("Confirm")');
  
  // Wait a bit for the request
  await page.waitForTimeout(2000);
  
  await browser.close();
})();
