const puppeteer = require('../frontend/node_modules/puppeteer-core');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('Testing Cytoscape interactions...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1400,900']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900 });

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForSelector('.sidebar');

  // Go to Graph Investigation
  const navItems = await page.$$('.nav-item');
  for (const item of navItems) {
    const text = await page.evaluate(el => el.textContent, item);
    if (text && text.includes('Graph Investigation')) {
      await item.click();
      break;
    }
  }

  await page.waitForSelector('canvas');
  console.log('Canvas loaded.');

  // Wait 2s for graph layout
  await new Promise(r => setTimeout(r, 2000));

  // Click on canvas center to trigger node click or search for a node
  console.log('Searching for an address to select and open dossier...');
  await page.type('input[placeholder="Search address, TXID, or IP..."]', '1');
  await new Promise(r => setTimeout(r, 600));

  // Click first autocomplete result
  await page.waitForSelector('div[style*="z-index: 40"] div');
  const firstResult = await page.$('div[style*="z-index: 40"] div');
  if (firstResult) {
    await firstResult.click();
    console.log('Clicked search result.');
  }

  // Wait for dossier drawer to open
  await new Promise(r => setTimeout(r, 800));

  // Check if dossier drawer appeared
  const dossierText = await page.evaluate(() => {
    const drawer = document.querySelector('div[style*="width: 380px"]');
    return drawer ? drawer.innerText : null;
  });

  console.log('Dossier content detected:', !!dossierText);
  if (!dossierText) {
    throw new Error('Dossier drawer did not open on node selection!');
  }
  console.log('Dossier snippet:', dossierText.slice(0, 250));

  // Verify expansion buttons exist
  const hasExpand1Hop = dossierText.includes('+1 Hop');
  const hasExpand2Hops = dossierText.includes('+2 Hops');
  const hasExpand3Hops = dossierText.includes('+3 Hops');
  console.log('Expansion buttons present:', { '+1 Hop': hasExpand1Hop, '+2 Hops': hasExpand2Hops, '+3 Hops': hasExpand3Hops });

  if (!hasExpand1Hop || !hasExpand2Hops || !hasExpand3Hops) {
    throw new Error('Expansion buttons missing from dossier!');
  }

  // Test clicking +1 Hop expansion
  console.log('Clicking +1 Hop expansion...');
  const expandBtn = await page.evaluateHandle(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    return btns.find(b => b.textContent.trim() === '+1 Hop');
  });

  if (expandBtn) {
    await expandBtn.click();
    await new Promise(r => setTimeout(r, 1500));
    console.log('Expansion button clicked successfully.');
  }

  // Test toolbar zoom and fit
  console.log('Testing toolbar Zoom In (+)...');
  const zoomInBtn = await page.evaluateHandle(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    return btns.find(b => b.textContent.trim() === '+');
  });
  if (zoomInBtn) await zoomInBtn.click();

  console.log('Testing toolbar Fit...');
  const fitBtn = await page.evaluateHandle(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    return btns.find(b => b.textContent.trim() === '⛶ Fit');
  });
  if (fitBtn) await fitBtn.click();

  // Take screenshot with dossier open
  const screenshotPath = path.join(__dirname, '..', 'reports', 'node_dossier_verified.png');
  await page.screenshot({ path: screenshotPath });
  console.log(`Saved dossier verification screenshot to: ${screenshotPath}`);

  await browser.close();
  console.log('INTERACTION TESTS COMPLETED SUCCESSFULLY!');
})().catch(err => {
  console.error('Interaction test failed:', err);
  process.exit(1);
});
