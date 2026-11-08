Product Requirements Document (PRD)

Cafe24 E-commerce Web Scraper & Automated Image Processor

Document Information

Details

Project Name

Cafe24 Product Data Scraper & Image Editor

Target Platform

E-commerce sites built on the Cafe24 platform (Korean E-commerce solution)

Version

1.1 (Refined)

Date

October 28, 2025

Stakeholder

Client / Data Integration Team

1. Introduction and Project Goals

The core objective is to develop a highly reliable Python-based web scraper that extracts comprehensive product data from a specified Cafe24-hosted e-commerce website. The critical second stage is the automated image processing workflow designed to clean, crop, and resize long product detail images, preparing all extracted data and assets for bulk upload to Shopify.

1.1 Key Objectives

Achieve high-reliability data extraction by deploying advanced anti-scraping measures.

Extract all necessary product fields, variants, and image URLs.

Automate image refinement to surgically remove supplier/policy blocks from detail images.

Deliver final output in a Shopify-compatible format (CSV/Excel + compressed images).

2. Technical Requirements and Strategy

2.1 Technology Stack (Mandatory)

| Requirement       | Detail                                                                      |
| ----------------- | ---------------------------------------------------------------------------- |
| Core Language     | Python 3.x                                                                  |
| Scraping Framework| Scrapy (preferred) with Playwright/Selenium fallback for dynamic content     |
| Image Processing  | Pillow (PIL) for cropping/resizing; OpenCV (cv2) for pattern matching        |
| Anti-Scraping     | Rotating residential proxy pool with credential management                  |
| Output            | pandas for structured data handling and CSV/Excel generation                |

2.2 Anti-Scraping Operations (Detailed)

The implementation must strictly follow these strategies to ensure continuous, reliable data extraction:

| Requirement      | Detailed Implementation                                                                                              | Operational Notes                                                                                                      |
| ---------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| IP Blocking      | Implement a rotating residential proxy pool; each request uses a fresh IP with automatic blacklisting of failed nodes | Proxy provider to be confirmed (default assumption: Smartproxy). API key supplied via environment variables.           |
| Bot Detection    | Randomized delay (3–10s), realistic user-agent rotation, and browser header spoofing                                  | Maintain request cadence < 60 req/min. Persist failed URLs for retry queue.                                            |
| Dynamic Content  | Attempt Scrapy fetch first; auto-fallback to Playwright/Selenium headless render when JS is required                  | Limit concurrent headless sessions to 3. Capture HAR logs for pages requiring JS.                                      |
| CAPTCHA Handling | Integrate third-party solver (e.g., 2Captcha) as contingency                                                          | Trigger only after two failed attempts; log CAPTCHA events with timestamp and target URL.                              |

Additional operational requirements:

- **Provider + Budget Confirmation:** Client to confirm proxy and CAPTCHA vendors plus monthly request ceilings before Phase 1 kickoff. Defaults can be overridden via config without code changes.
- **Rotation Cadence:** Configure 1 request/IP minimum before rotation with adaptive back-off when HTTP 403/429 responses exceed 2% of requests.
- **Audit Logging:** Persist anti-scraping events (IP bans, CAPTCHA triggers, Playwright fallbacks) to `logs/anti_scraping.log` for monitoring.

3. Data Extraction and Shopify Schema

3.1 Data Fields to be Extracted and Mapped

Data must be extracted and mapped to the standard Shopify CSV columns to ensure seamless bulk import.

| Source Field / Generated Value        | Shopify CSV Column(s)                        | Description                                                                                          | Requirement |
| ------------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------- |
| Product Title                         | Title                                        | Full product name.                                                                                  | Mandatory   |
| URL Slug / Generated Handle           | Handle                                       | Lowercase, hyphenated unique identifier for the product.                                            | Mandatory   |
| Product Type                          | Product Type                                 | Shopify category grouping.                                                                           | Mandatory   |
| Brand / Supplier Name                 | Vendor                                       | Merchant or brand attribution.                                                                       | Mandatory   |
| Tags (comma-separated)                | Tags                                         | Keywords derived from source metadata.                                                               | Mandatory   |
| Publish Flag (bool)                   | Published                                    | Indicates whether product should be live after import.                                               | Mandatory   |
| SKU / Identifier                      | Variant SKU                                  | Unique inventory code per variant.                                                                   | Mandatory   |
| Inventory Quantity                    | Variant Inventory Qty                        | Current stock level when available; default to 0 if unknown.                                         | Mandatory   |
| Inventory Policy (e.g., continue)     | Variant Inventory Policy                     | Controls oversell behavior.                                                                          | Mandatory   |
| Fulfillment Service                   | Variant Fulfillment Service                  | Typically `manual`.                                                                                  | Mandatory   |
| Regular Price                         | Variant Price                                | Current sell price.                                                                                  | Mandatory   |
| Sale Price                            | Variant Compare At Price                     | Original price when on sale; otherwise left blank.                                                   | Conditional |
| Requires Shipping (bool)              | Variant Requires Shipping                    | True if physical product.                                                                            | Mandatory   |
| Weight + Unit                         | Variant Grams / Weight Unit                  | Shipping weight converted to grams (Shopify requires grams).                                          | Mandatory   |
| Option Name(s) (e.g., Color, Size)    | Option1 Name / Option2 Name / Option3 Name   | Variant option headers.                                                                              | Mandatory   |
| Option Value(s)                       | Option1 Value / Option2 Value / Option3 Value| Specific variant values.                                                                             | Mandatory   |
| Main Image Downloaded Filename        | Image Src / Image Position / Image Alt Text  | High-res main image stored locally; script populates URL path (position 1) and optional alt text.     | Mandatory   |
| Additional Image Filenames (if any)   | Image Src / Image Position                   | Other gallery images following positional order.                                                      | Conditional |
| Processed Detail Image Filename       | Body (HTML)                                  | Injected via `<img>` tag pointing to processed detail image path.                                    | Mandatory   |
| HTML Product Description              | Body (HTML)                                  | Cleaned description plus embedded processed detail image.                                            | Mandatory   |

4. Critical Feature: Automated Image Editing & Refinement

The image processing module, utilizing Pillow and OpenCV, must ensure the long detail page image is cleaned of extraneous content.

4.1 Detail Image Cropping Logic (Refined)

The process must be executed for every downloaded detail image:

Template Creation: A small template image of the common supplier/policy information block will be manually provided.

Pattern Matching (OpenCV): The script loads the detail image and the template. It uses cv2.matchTemplate with the cv2.TM_CCOEFF_NORMED method to find the highest correlation region. This returns the precise coordinates $(x, y)$ of the template's match within the target image.

Boundary Identification: Calculate the precise $y$-coordinate where the common supplier information ends. This is determined by $y_{\text{end}} = y_{\text{top}} + h_{\text{template}} + \epsilon$, where $\epsilon$ is a small buffer (e.g., 10 pixels) to clear any residual border.

Automated Cropping (Pillow): The script uses the Pillow library to slice the original image. The final crop box will start at $(0, y_{\text{end}})$, extending to the full width and the original height of the image.

Saving Final Image: Save the cropped image as a new file (e.g., SKU_detail_cropped.jpg) with optimized quality/compression settings.

Template management and fallbacks:

- Store the supplier template image in `assets/templates/detail_header.png` and version it in source control.
- Persist template metadata (hash, dimensions, last update) in `config/image_template.json` to detect drift.
- If `matchTemplate` returns < 0.8 confidence or multiple matches, log the event, skip cropping, and flag the product in the QA report for manual review.

5. Deliverables and Acceptance Criteria

5.1 Final Deliverables and Output Structure

Structured Data File: A single file (shopify_import_data.csv or .xlsx) containing all extracted and mapped data points, ready for direct bulk import.

Compressed Image Folder (images.zip): A .zip archive containing:

Main Product Images: Original high-resolution images (e.g., SKU_main_1.jpg).

Processed Detail Images: The final, automatically cropped files (e.g., SKU_detail_cropped.jpg).

Execution Report: A JSON/CSV log summarizing run statistics (success count, failure count, CAPTCHA triggers, proxy rotates) plus an error report listing any products requiring manual follow-up.

5.2 Acceptance Criteria

Accuracy: Data accuracy (price, SKU, options) is verified to be 99%+.

Completeness: All 200 (or 300) products have been successfully extracted. Phase 3 interim testing may sample 10 products, but final acceptance requires 100% compliance.

Image Integrity (CRITICAL): For 100% of processed detail images, the common supplier/policy information is successfully identified and removed, leaving only the pure product description visible.

Format: The final structured file is ready for direct Shopify bulk upload.

6. Project Scope and Estimation

| Scenario       | Fixed Price Quote | Estimated Completion Time |
| -------------- | ----------------- | ------------------------- |
| 200 Products   | **TBD**           | **TBD**                   |
| 300 Products   | **TBD**           | **TBD**                   |

7. Project Milestones and Phases (New)

The project execution will be broken into four sequential phases, with Phase 3 being the most critical and complex.

Phase

Milestone

Acceptance Criteria

Phase 1: Setup & Authentication

Successfully configure environment and bypass initial anti-scraping checks on a single product page.

Residential proxy pool is integrated. Headless browser fallback is confirmed. Data for one product is extracted successfully into a Python object.

Phase 2: Core Data Extraction

Extract all required data fields (Titles, SKUs, Options, Prices) for the full product catalog (200/300 products).

100% of target product URLs have been scraped and data is saved to a preliminary structure (e.g., JSON/List of Dicts).

Phase 3: Image Processing & Refinement (CRITICAL)

Fully implement the OpenCV pattern matching and Pillow cropping logic.

Image Integrity Acceptance Criterion met for QA sample (minimum 10 products) with zero failures. Any sample issues must be resolved before proceeding. All images are downloaded and saved locally.

Phase 4: Finalization & Delivery

Generate the final Shopify CSV/Excel file and the compressed image folder.

Final deliverables (Section 5.1) are completed and submitted. Data mapping to Shopify columns is verified correct.