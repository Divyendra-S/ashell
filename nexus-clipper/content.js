// Content script — extracts article content from the current page
// Readability.js and Turndown.js are injected before this script via manifest

// --- Comment/reply stripping for social platforms ---

function stripComments(html, url) {
  const el = document.createElement("div");
  el.innerHTML = html;

  if (url.includes("x.com") || url.includes("twitter.com")) {
    // X/Twitter: the main post is in an <article> element.
    // Replies/comments are separate <article> elements or in a "Conversation" section.
    // Strategy: find the "Conversation" heading and remove everything after it.
    // Also remove profile cards, follow buttons, and reply threads.
    el.querySelectorAll('[data-testid="reply"], [data-testid="cellInnerDiv"]').forEach((n) => n.remove());
  }

  // Generic: remove common comment section selectors
  const commentSelectors = [
    "#comments", ".comments", ".comment-section", ".replies",
    '[class*="comment"]', '[id*="comment"]',
    ".disqus_thread", "#disqus_thread",
  ];
  commentSelectors.forEach((sel) => {
    try { el.querySelectorAll(sel).forEach((n) => n.remove()); } catch (_) {}
  });

  return el.innerHTML;
}

function stripMarkdownComments(markdown, url) {
  if (url.includes("x.com") || url.includes("twitter.com")) {
    // X/Twitter articles: the actual post content typically ends before
    // reply sections marked by "## Conversation", "## Post", or profile image patterns
    // from other users replying. Cut at known reply markers.
    const markers = [
      /\n## Conversation\n/i,
      /\n## Replies\n/i,
    ];
    for (const marker of markers) {
      const match = markdown.match(marker);
      if (match) {
        // Keep the content before "## Conversation" but also grab the actual post
        // which is usually after "## Post" and before "## Conversation"
        const parts = markdown.split(marker);
        // Check if there's a "## Post" section — if so, the real content is between Post and Conversation
        const postMatch = parts[0].match(/\n## Post\n/i);
        if (postMatch) {
          const afterPost = parts[0].split(/\n## Post\n/i)[1];
          // But also keep content before ## Post if it's the main article text
          const beforePost = parts[0].split(/\n## Post\n/i)[0];
          // For X articles, the meat is usually after "## Post"
          markdown = (beforePost.trim().length > 200 ? beforePost + "\n\n" : "") + afterPost;
        } else {
          markdown = parts[0];
        }
        break;
      }
    }
  }
  return markdown.trim();
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action !== "extract") return false;

  try {
    const url = window.location.href;

    // Clone the document so Readability doesn't mutate the live DOM
    const docClone = document.cloneNode(true);
    const reader = new Readability(docClone);
    const article = reader.parse();

    if (!article || !article.content) {
      sendResponse({ error: "Could not extract article content from this page." });
      return true;
    }

    // Strip comments from HTML before converting to markdown
    const cleanHtml = stripComments(article.content, url);

    // Convert HTML to markdown
    const turndown = new TurndownService({
      headingStyle: "atx",
      codeBlockStyle: "fenced",
      bulletListMarker: "-",
    });

    // Keep code blocks intact
    turndown.addRule("pre", {
      filter: ["pre"],
      replacement: (content, node) => {
        const code = node.querySelector("code");
        const lang = code?.className?.match(/language-(\w+)/)?.[1] || "";
        const text = code ? code.textContent : node.textContent;
        return `\n\`\`\`${lang}\n${text}\n\`\`\`\n`;
      },
    });

    let markdown = turndown.turndown(cleanHtml);

    // Post-process: strip reply/comment sections from markdown
    markdown = stripMarkdownComments(markdown, url);

    sendResponse({
      title: article.title || document.title,
      url,
      content: markdown,
      excerpt: article.excerpt || "",
      byline: article.byline || "",
      wordCount: markdown.split(/\s+/).length,
    });
  } catch (err) {
    sendResponse({ error: err.message });
  }

  return true; // keep message channel open for async response
});
