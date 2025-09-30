const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 393, height: 852 } // iPhone 16 Pro size
  });
  const page = await context.newPage();
  
  await page.goto('http://localhost:5173');
  
  // Wait for page to load
  await page.waitForTimeout(2000);
  
  // Navigate to growth page if needed
  try {
    await page.click('button:has-text("Where can we grow")');
    await page.waitForTimeout(1000);
  } catch (e) {
    console.log('Growth page button not found, assuming already on growth page');
  }
  
  await page.screenshot({ path: 'current-layout.png', fullPage: true });
  console.log('Screenshot saved as current-layout.png');
  
  await browser.close();
})();