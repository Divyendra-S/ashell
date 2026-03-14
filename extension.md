# Kuro Chrome Extension — Implementation Plan

## What It Does

User reads any page (X thread, blog, arxiv, docs) → clicks extension → content is extracted → sent to Kuro backend for saving or discussion.

```
Any webpage (X, Medium, arxiv, docs, etc.)
  → User clicks Kuro extension icon
  → Content script extracts clean text from DOM
  → Popup shows: [Save to Kuro] [Discuss on Kuro]
  → Save: POST /api/ingest/extension → stored in memory
  → Discuss: opens kuro web app with article pre-loaded in context
```

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Chrome Extension                           │
│                                             │
│  ┌──────────────┐    ┌──────────────────┐   │
│  │ Content      │    │ Popup            │   │
│  │ Script       │───▶│ (popup.html)     │   │
│  │              │    │                  │   │
│  │ - Readability│    │ [Save to Kuro]   │   │
│  │ - X thread   │    │ [Discuss on Kuro]│   │
│  │   unroller   │    │ [Select text]    │   │
│  └──────────────┘    └────────┬─────────┘   │
│                               │             │
│  ┌────────────────────────────▼──────────┐  │
│  │ Background Service Worker             │  │
│  │ - Receives extracted content          │  │
│  │ - POSTs to Kuro backend              │  │
│  │ - Handles auth token                  │  │
│  └────────────────────────────┬──────────┘  │
└───────────────────────────────┼──────────────┘
                                │
                    POST /api/ingest/extension
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Kuro Backend         │
                    │  (FastAPI)            │
                    │                       │
                    │  → ingest agent       │
                    │  → store in memory    │
                    │  → index embeddings   │
                    └───────────────────────┘
```

---

## Directory Structure

```
kuro-extension/
  manifest.json          # Extension manifest (Manifest V3)
  background.js          # Service worker: API calls to Kuro backend
  content.js             # Content script: DOM text extraction
  popup/
    popup.html           # Extension popup UI
    popup.js             # Popup logic: buttons, status
    popup.css            # Minimal styling
  extractors/
    readability.js       # Mozilla Readability.js (bundled, for articles)
    twitter.js           # X/Twitter thread extractor
    generic.js           # Fallback: document.body.innerText with cleanup
  icons/
    icon16.png
    icon48.png
    icon128.png
```

---

## Manifest (`manifest.json`)

```json
{
  "manifest_version": 3,
  "name": "Kuro — Save & Study",
  "version": "1.0.0",
  "description": "Save any webpage or X thread to Kuro for study and discussion",
  "permissions": [
    "activeTab",
    "storage"
  ],
  "host_permissions": [
    "http://localhost:8000/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["extractors/generic.js", "content.js"],
      "run_at": "document_idle"
    },
    {
      "matches": ["*://x.com/*", "*://twitter.com/*"],
      "js": ["extractors/twitter.js", "content.js"],
      "run_at": "document_idle"
    }
  ],
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

---

## Content Script (`content.js`)

Extracts clean text from the current page. Uses site-specific extractors when available, falls back to Readability.js, then generic.

```javascript
// content.js — runs on every page, listens for extraction requests

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extract") {
    const result = extractPageContent();
    sendResponse(result);
  }
  return true; // async response
});

function extractPageContent() {
  const url = window.location.href;
  const hostname = window.location.hostname;

  // Site-specific extractors
  if (hostname === "x.com" || hostname === "twitter.com") {
    return extractTwitterThread();
  }

  // Try Readability.js for articles
  try {
    const article = extractWithReadability();
    if (article && article.content.length > 100) {
      return article;
    }
  } catch (e) {}

  // Fallback: generic extraction
  return extractGeneric();
}
```

---

## X/Twitter Extractor (`extractors/twitter.js`)

Reads tweet text directly from the DOM. No API needed — the browser already rendered the content.

```javascript
function extractTwitterThread() {
  // Tweet text lives in elements with data-testid="tweetText"
  const tweetElements = document.querySelectorAll('[data-testid="tweetText"]');

  if (tweetElements.length === 0) {
    return { error: "No tweets found on this page" };
  }

  // Get author from the page
  const authorEl = document.querySelector('[data-testid="User-Name"]');
  const author = authorEl ? authorEl.innerText.split("\n")[0] : "Unknown";

  // Extract each tweet's text in order
  const tweets = [];
  tweetElements.forEach((el, index) => {
    const text = el.innerText.trim();
    if (text) {
      tweets.push({ index: index + 1, text });
    }
  });

  // Handle "Show more" buttons — click them to expand
  const showMoreButtons = document.querySelectorAll('[data-testid="tweet-text-show-more-link"]');
  showMoreButtons.forEach(btn => btn.click());

  // Re-extract after expanding if any were clicked
  if (showMoreButtons.length > 0) {
    setTimeout(() => {
      tweetElements.forEach((el, index) => {
        tweets[index] = { index: index + 1, text: el.innerText.trim() };
      });
    }, 500);
  }

  // Build clean thread text
  const threadText = tweets.map(t => `[${t.index}] ${t.text}`).join("\n\n");

  return {
    url: window.location.href,
    title: `Thread by ${author}`,
    content: threadText,
    type: "twitter_thread",
    author: author,
    tweet_count: tweets.length,
    extracted_at: new Date().toISOString()
  };
}
```

---

## Readability Extractor (`extractors/readability.js`)

For blogs, articles, docs — extracts the main content, strips nav/ads/sidebar.

```javascript
// Bundle Mozilla's Readability.js (https://github.com/mozilla/readability)
// ~15KB, no dependencies

function extractWithReadability() {
  // Clone the document so Readability doesn't modify the live DOM
  const docClone = document.cloneNode(true);
  const reader = new Readability(docClone);
  const article = reader.parse();

  if (!article) return null;

  return {
    url: window.location.href,
    title: article.title,
    content: article.textContent,       // Clean text, no HTML
    html_content: article.content,      // HTML if we want to convert to markdown server-side
    type: "article",
    byline: article.byline || null,
    excerpt: article.excerpt || null,
    site_name: article.siteName || window.location.hostname,
    word_count: article.textContent.split(/\s+/).length,
    extracted_at: new Date().toISOString()
  };
}
```

---

## Generic Extractor (`extractors/generic.js`)

Fallback for pages where Readability fails (SPAs, dashboards, etc.).

```javascript
function extractGeneric() {
  // Try semantic elements first
  const mainEl = document.querySelector("main")
    || document.querySelector("article")
    || document.querySelector('[role="main"]')
    || document.body;

  // Remove noise elements
  const clone = mainEl.cloneNode(true);
  const noiseSelectors = [
    "nav", "header", "footer", "aside",
    '[role="navigation"]', '[role="banner"]',
    ".sidebar", ".nav", ".menu", ".ad", ".advertisement",
    "script", "style", "noscript"
  ];
  noiseSelectors.forEach(sel => {
    clone.querySelectorAll(sel).forEach(el => el.remove());
  });

  const text = clone.innerText
    .replace(/\n{3,}/g, "\n\n")    // collapse excessive newlines
    .trim();

  return {
    url: window.location.href,
    title: document.title,
    content: text,
    type: "generic",
    word_count: text.split(/\s+/).length,
    extracted_at: new Date().toISOString()
  };
}
```

---

## Popup UI (`popup/popup.html`)

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="popup.css">
</head>
<body>
  <div class="container">
    <h1>Kuro</h1>

    <div id="preview">
      <p id="page-title" class="title">Loading...</p>
      <p id="page-info" class="info"></p>
    </div>

    <div id="actions">
      <button id="btn-save" class="btn btn-primary">Save to Kuro</button>
      <button id="btn-discuss" class="btn btn-secondary">Discuss on Kuro</button>
    </div>

    <div id="status" class="hidden">
      <p id="status-text"></p>
    </div>

    <div id="settings">
      <label>
        <input type="checkbox" id="auto-embed" checked>
        Generate embeddings on save
      </label>
    </div>
  </div>

  <script src="popup.js"></script>
</body>
</html>
```

---

## Popup Logic (`popup/popup.js`)

```javascript
const KURO_API = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", async () => {
  // Get current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Extract content from the page
  const response = await chrome.tabs.sendMessage(tab.id, { action: "extract" });

  if (response.error) {
    showStatus(response.error, "error");
    return;
  }

  // Show preview
  document.getElementById("page-title").textContent = response.title;
  document.getElementById("page-info").textContent =
    `${response.type} · ${response.word_count || "?"} words`;

  // Store extracted content for button handlers
  window.extractedContent = response;

  // Button handlers
  document.getElementById("btn-save").addEventListener("click", () => saveToKuro(response));
  document.getElementById("btn-discuss").addEventListener("click", () => discussOnKuro(response));
});

async function saveToKuro(content) {
  showStatus("Saving...", "loading");

  try {
    const resp = await fetch(`${KURO_API}/api/ingest/extension`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: content.url,
        title: content.title,
        content: content.content,
        type: content.type,
        metadata: {
          author: content.author || content.byline,
          tweet_count: content.tweet_count,
          word_count: content.word_count,
          site_name: content.site_name,
        }
      })
    });

    const result = await resp.json();
    showStatus(`Saved! ${result.concepts_extracted || 0} concepts extracted.`, "success");
  } catch (e) {
    showStatus(`Error: ${e.message}`, "error");
  }
}

async function discussOnKuro(content) {
  showStatus("Preparing discussion...", "loading");

  try {
    // Save first, get article ID back
    const resp = await fetch(`${KURO_API}/api/ingest/extension`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: content.url,
        title: content.title,
        content: content.content,
        type: content.type,
        discuss: true  // flag to pre-load in chat context
      })
    });

    const result = await resp.json();

    // Open Kuro web app with article in context
    chrome.tabs.create({
      url: `${KURO_API}/chat?article_id=${result.article_id}&mode=discuss`
    });
  } catch (e) {
    showStatus(`Error: ${e.message}`, "error");
  }
}

function showStatus(message, type) {
  const statusEl = document.getElementById("status");
  const textEl = document.getElementById("status-text");
  statusEl.classList.remove("hidden");
  textEl.textContent = message;
  textEl.className = type;
}
```

---

## Background Service Worker (`background.js`)

```javascript
// background.js — handles API communication and auth

// Store API settings
chrome.storage.local.get(["kuro_api_url"], (result) => {
  if (!result.kuro_api_url) {
    chrome.storage.local.set({ kuro_api_url: "http://localhost:8000" });
  }
});

// Handle messages from popup that need background processing
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "checkConnection") {
    checkKuroConnection().then(sendResponse);
    return true;
  }
});

async function checkKuroConnection() {
  try {
    const { kuro_api_url } = await chrome.storage.local.get("kuro_api_url");
    const resp = await fetch(`${kuro_api_url}/health`);
    return { connected: resp.ok };
  } catch {
    return { connected: false };
  }
}
```

---

## Backend Endpoint (`kuro/web/app.py`)

New endpoint to receive content from the extension.

```python
@app.post("/api/ingest/extension")
async def ingest_from_extension(payload: ExtensionPayload):
    """
    Receives extracted content from the Chrome extension.
    Runs it through the ingest agent for entity/concept extraction.
    """
    # Save article to disk
    file_path = article_store.save_article(
        title=payload.title,
        content=payload.content,
        topic=infer_topic(payload.title, payload.content)
    )

    # Store article record in DB
    article_id = store.add_article(
        url=payload.url,
        title=payload.title,
        file_path=file_path
    )

    # Run ingest agent for concept extraction
    result = await ingest_agent.run(
        message=f"Extract concepts from this article: {payload.title}\n\n{payload.content}",
        store=store
    )

    # Generate embeddings for semantic search
    chunks = chunk_text(payload.content, max_tokens=500)
    for chunk in chunks:
        semantic_search.index_article_chunk(article_id, chunk)

    return {
        "article_id": article_id,
        "title": payload.title,
        "file_path": file_path,
        "concepts_extracted": result.get("concept_count", 0),
        "chunks_indexed": len(chunks)
    }


class ExtensionPayload(BaseModel):
    url: str
    title: str
    content: str
    type: str                              # "twitter_thread" | "article" | "generic"
    discuss: bool = False
    metadata: dict | None = None
```

---

## Deep Link: Discuss Mode

When user clicks "Discuss on Kuro", the web app opens with the article pre-loaded.

```
URL: /chat?article_id=123&mode=discuss

Backend handles this by:
1. Looking up article_id → loads content + extracted concepts
2. Pre-populating the study agent's context with the article
3. Study agent starts with: "I've loaded [Article Title]. What would you like to discuss?"
```

```python
@app.get("/chat")
async def chat_page(article_id: int = None, mode: str = None):
    """Serve chat UI, optionally pre-loaded with an article."""
    context = {}
    if article_id:
        article = store.get_article(article_id)
        concepts = store.get_concepts_for_article(article_id)
        context = {
            "article": article,
            "concepts": concepts,
            "mode": mode or "discuss",
            "initial_message": f"I've loaded '{article['title']}'. What would you like to discuss?"
        }
    return templates.TemplateResponse("index.html", {"context": context})
```

---

## Build Order

| Step | What | Notes |
|------|------|-------|
| 1 | `manifest.json` + `popup/popup.html` | Skeleton extension, loads in Chrome |
| 2 | `extractors/generic.js` + `content.js` | Basic text extraction from any page |
| 3 | `popup/popup.js` + `background.js` | Save button → POST to backend |
| 4 | Backend `POST /api/ingest/extension` | Receives and processes content |
| 5 | `extractors/twitter.js` | X/Twitter thread unrolling |
| 6 | Bundle `extractors/readability.js` | Article extraction for blogs/docs |
| 7 | "Discuss on Kuro" flow | Deep link + pre-loaded chat context |
| 8 | Polish: error handling, loading states, settings | Production readiness |

---

## Key Technical Notes

- **No API keys needed for extraction** — content script reads from the DOM the browser already rendered
- **Works on paywalled content** — if the user can see it, the extension can extract it
- **X/Twitter DOM selectors** — `[data-testid="tweetText"]` for tweet text, `[data-testid="User-Name"]` for author. These are stable selectors X uses for testing
- **Readability.js** — Mozilla's library (~15KB), battle-tested, extracts article content and strips noise. Used by Firefox's Reader View
- **Manifest V3** — current Chrome extension standard, uses service workers instead of background pages
- **CORS** — backend needs `Access-Control-Allow-Origin` header for extension requests. Add `CORSMiddleware` to FastAPI
- **Text selection mode** (future) — let user select specific text on page instead of full extraction
