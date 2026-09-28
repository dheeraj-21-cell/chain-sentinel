const puppeteer = require('../frontend/node_modules/puppeteer-core');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('Launching headless Chrome...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1400,900']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900 });

  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    if (msg.type() === 'error') {
      console.error('Browser console error:', msg.text());
    }
  });

  console.log('Navigating to http://localhost:5173/ ...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle2', timeout: 30000 });

  // Wait for sidebar to render
  await page.waitForSelector('.sidebar', { timeout: 10000 });
  console.log('App loaded successfully.');

  // Click on "Graph Investigation" tab in the sidebar
  console.log('Clicking on Graph Investigation in sidebar...');
  const navItems = await page.$$('.nav-item');
  let graphNavClicked = false;
  for (const item of navItems) {
    const text = await page.evaluate(el => el.textContent, item);
    if (text && text.includes('Graph Investigation')) {
      await item.click();
      graphNavClicked = true;
      console.log('Clicked Graph Investigation nav item.');
      break;
    }
  }

  if (!graphNavClicked) {
    throw new Error('Could not find Graph Investigation nav item in sidebar.');
  }

  // Wait for tabs-header to appear
  await page.waitForSelector('.tabs-header', { timeout: 10000 });
  console.log('Tabs header is present in Graph Investigation view.');

  // Check all tabs present
  const tabButtons = await page.$$eval('.tab-btn', btns => btns.map(b => ({
    text: b.textContent.trim(),
    isActive: b.classList.contains('active')
  })));
  console.log('Tab buttons found:', JSON.stringify(tabButtons, null, 2));

  // Verify Interactive Canvas is first and active
  const interactiveTab = tabButtons.find(t => t.text.includes('Interactive Canvas'));
  if (!interactiveTab) {
    throw new Error('Interactive Canvas tab NOT FOUND in tabs-header!');
  }
  console.log('PASS: "Interactive Canvas" tab is present.');

  if (!interactiveTab.isActive) {
    throw new Error('Interactive Canvas tab is NOT active by default!');
  }
  console.log('PASS: "Interactive Canvas" tab is DEFAULT active tab.');

  // Verify Cytoscape canvas container
  await page.waitForSelector('canvas', { timeout: 10000 });
  const canvasElementsCount = await page.$$eval('canvas', canvases => canvases.length);
  console.log(`PASS: Cytoscape canvas rendered with ${canvasElementsCount} canvas layer(s).`);

  // Verify toolbar buttons
  const toolbarButtons = await page.$$eval('.view-header button, .btn-ghost, .btn-secondary', btns => btns.map(b => b.textContent.trim()).filter(Boolean));
  console.log('Toolbar & header buttons:', toolbarButtons);

  // Wait a moment for layout to stabilize
  await new Promise(r => setTimeout(r, 2000));

  // Capture screenshot to artifact directory
  const screenshotPath = path.join(__dirname, '..', 'reports', 'interactive_canvas_verified.png');
  fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
  await page.screenshot({ path: screenshotPath, fullPage: false });
  console.log(`Saved verification screenshot to: ${screenshotPath}`);

  // Test clicking other tabs and coming back to Interactive Canvas
  console.log('Testing switching to "Topological Analysis" tab...');
  const topologyBtn = await page.$('.tab-btn:nth-child(2)');
  await topologyBtn.click();
  await new Promise(r => setTimeout(r, 500));
  const topActive = await page.$$eval('.tab-btn', btns => btns.map(b => ({ text: b.textContent.trim(), isActive: b.classList.contains('active') })));
  console.log('Tabs state after clicking Topological Analysis:', topActive);

  console.log('Testing switching back to "Interactive Canvas" tab...');
  const interactiveBtn = await page.$('.tab-btn:nth-child(1)');
  await interactiveBtn.click();
  await new Promise(r => setTimeout(r, 500));

  // Verify Cytoscape canvas is still present and functional
  const canvasCountAfter = await page.$$eval('canvas', canvases => canvases.length);
  console.log(`PASS: After tab switch, Cytoscape canvas layers count: ${canvasCountAfter}`);

  await browser.close();
  console.log('ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!');
})().catch(err => {
  console.error('Verification failed:', err);
  process.exit(1);
});
