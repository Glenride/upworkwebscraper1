import puppeteer from 'puppeteer';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { parse } from 'csv-parse/sync';
import slugify from 'slugify';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEFAULT_INPUT = path.resolve(__dirname, '../urls.csv');
const DEFAULT_OUTPUT = path.resolve(__dirname, '../web-scraper-python/output/screenshots');

const parseArgs = () => {
  const args = process.argv.slice(2);
  const options = {};
  for (let i = 0; i < args.length; i += 1) {
    if (args[i].startsWith('--')) {
      const key = args[i].slice(2);
      const value = args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true;
      options[key] = value;
      if (value !== true) {
        i += 1;
      }
    }
  }
  return options;
};

const ensureDirectory = async (dir) => {
  await fs.mkdir(dir, { recursive: true });
};

const readInputCsv = async (filePath) => {
  const content = await fs.readFile(filePath, 'utf-8');
  const records = parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
  });

  return records
    .map((record) => ({
      store: record.store_name || record.store || record.Store || 'store',
      url: record.url || record.URL || record.link || record.Link,
    }))
    .filter((record) => record.url);
};

const captureProductScreenshots = async ({ inputPath, outputDir, viewport }) => {
  const rows = await readInputCsv(inputPath);
  if (!rows.length) {
    console.warn('No URLs found in input file:', inputPath);
    return;
  }

  await ensureDirectory(outputDir);

  const browser = await puppeteer.launch({
    headless: true,
    defaultViewport: viewport,
  });

  const page = await browser.newPage();
  await page.setUserAgent(
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
  );

  for (const row of rows) {
    const slug = slugify(row.store || row.url, { lower: true, strict: true });
    const mainScreenshotPath = path.join(outputDir, `${slug}-full.png`);
    const detailScreenshotPath = path.join(outputDir, `${slug}-detail.png`);

    try {
      console.log(`Navigating to ${row.url}`);
      await page.goto(row.url, { waitUntil: 'networkidle2', timeout: 90000 });
      await new Promise((resolve) => setTimeout(resolve, 2000));

      await page.screenshot({ path: mainScreenshotPath, fullPage: true });

      const detailSection = await page.$('#prdDetail, #prdDetailContentLazy, .productDetail, .prdDetail');
      if (detailSection) {
        await detailSection.screenshot({ path: detailScreenshotPath });
      } else {
        console.warn(`Detail section not found for ${row.url}`);
      }

      console.log(`Saved screenshots for ${row.url}`);
    } catch (error) {
      console.error(`Failed to capture ${row.url}:`, error.message);
    }
  }

  await browser.close();
};

const main = async () => {
  const args = parseArgs();
  const inputPath = path.resolve(args.input || DEFAULT_INPUT);
  const outputDir = path.resolve(args.output || DEFAULT_OUTPUT);
  const viewport = {
    width: Number.parseInt(args.width, 10) || 1280,
    height: Number.parseInt(args.height, 10) || 720,
  };

  await captureProductScreenshots({ inputPath, outputDir, viewport });
};

main().catch((error) => {
  console.error('Unhandled error during Puppeteer run:', error);
  process.exitCode = 1;
});
