// Popup script — auth, article extraction, duplicate detection, save

const $ = (id) => document.getElementById(id);

let extractedData = null;
let currentUser = null; // { access_token, user_id, email }

// ─── Views ───

function showView(id) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  $(id).classList.add("active");
}

// ─── Supabase Auth (direct REST, no SDK) ───

async function supabaseAuth(endpoint, body) {
  const res = await fetch(`${CONFIG.SUPABASE_URL}/auth/v1/${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: CONFIG.SUPABASE_KEY,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error_description || data.msg || data.message || "Auth failed");
  return data;
}

async function login(email, password) {
  const data = await supabaseAuth("token?grant_type=password", { email, password });
  const userId = data.user?.user_metadata?.username || email.split("@")[0];
  const session = {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    user_id: userId,
    email: data.user.email,
  };
  await chrome.storage.local.set({ nexus_session: session });
  return session;
}

async function signup(email, password, username) {
  const data = await supabaseAuth("signup", {
    email,
    password,
    data: { username },
  });
  if (data.access_token) {
    // Auto-confirmed (no email verification needed)
    const session = {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      user_id: username,
      email: data.user.email,
    };
    await chrome.storage.local.set({ nexus_session: session });
    return session;
  }
  // Email confirmation required
  return null;
}

async function loadSession() {
  const { nexus_session } = await chrome.storage.local.get("nexus_session");
  return nexus_session || null;
}

async function logout() {
  await chrome.storage.local.remove("nexus_session");
  currentUser = null;
  $("userBadge").style.display = "none";
  showView("loginView");
}

// ─── Duplicate Check ───

async function checkIfSaved(url, userId) {
  const apiUrl = $("apiUrl")?.value?.replace(/\/+$/, "") || CONFIG.API_URL;
  try {
    const res = await fetch(
      `${apiUrl}/api/check-article?url=${encodeURIComponent(url)}&user_id=${encodeURIComponent(userId)}`
    );
    if (res.ok) {
      const data = await res.json();
      return data.saved;
    }
  } catch (_) {}
  return false;
}

// ─── Settings ───

async function loadSettings() {
  const defaults = { nexus_apiUrl: CONFIG.API_URL, nexus_topic: "general", nexus_autoExtract: true };
  const stored = await chrome.storage.local.get(defaults);
  $("apiUrl").value = stored.nexus_apiUrl;
  $("topic").value = stored.nexus_topic;
  $("autoExtract").checked = stored.nexus_autoExtract;
}

function saveSettings() {
  chrome.storage.local.set({
    nexus_apiUrl: $("apiUrl").value.replace(/\/+$/, ""),
    nexus_topic: $("topic").value,
    nexus_autoExtract: $("autoExtract").checked,
  });
}

// ─── Article Extraction ───

async function extractArticle() {
  showView("loadingView");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || tab.url?.startsWith("chrome://")) {
    showError("Cannot extract from this page.");
    return;
  }

  chrome.tabs.sendMessage(tab.id, { action: "extract" }, async (response) => {
    if (chrome.runtime.lastError) {
      showError("Content script not loaded. Try refreshing the page.");
      return;
    }
    if (response?.error) {
      showError(response.error);
      return;
    }

    extractedData = response;
    showPreview(response);

    // Check if already saved
    const alreadySaved = await checkIfSaved(response.url, currentUser.user_id);
    if (alreadySaved) {
      $("savedBadge").style.display = "inline-flex";
      $("saveBtn").textContent = "Already Saved";
      $("saveBtn").disabled = true;
    }
  });
}

function showPreview(data) {
  $("title").textContent = data.title;
  $("meta").textContent = `${data.wordCount} words | ${new URL(data.url).hostname}`;
  $("excerpt").textContent = data.excerpt || data.content.slice(0, 200);
  showView("mainView");
}

function showError(msg) {
  $("errorMsg").textContent = msg;
  showView("errorView");
}

function setStatus(text, type) {
  const el = $("status");
  el.textContent = text;
  el.className = `status ${type}`;
}

// ─── Save Article ───

$("saveBtn").addEventListener("click", async () => {
  if (!extractedData || !currentUser) return;

  const btn = $("saveBtn");
  btn.disabled = true;
  btn.textContent = "Saving...";
  setStatus("Sending to Nexus...", "saving");

  const apiUrl = $("apiUrl").value.replace(/\/+$/, "");
  const payload = {
    url: extractedData.url,
    title: extractedData.title,
    content: extractedData.content,
    topic: $("topic").value,
    user_id: currentUser.user_id,
    auto_extract: $("autoExtract").checked,
  };

  try {
    const res = await fetch(`${apiUrl}/api/ingest-article`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`${res.status}: ${err}`);
    }

    const data = await res.json();

    if (data.duplicate) {
      btn.textContent = "Already Saved";
      setStatus("This article was already in your knowledge graph.", "success");
      $("savedBadge").style.display = "inline-flex";
    } else {
      btn.textContent = "Saved!";
      setStatus(`Article saved (ID: ${data.article_id})`, "success");
      $("savedBadge").style.display = "inline-flex";
    }
  } catch (err) {
    btn.textContent = "Save to Nexus";
    btn.disabled = false;
    setStatus(`Error: ${err.message}`, "error");
  }
});

// ─── Auth UI ───

$("loginBtn").addEventListener("click", async () => {
  const email = $("loginEmail").value.trim();
  const password = $("loginPassword").value;
  if (!email || !password) {
    $("loginStatus").textContent = "Enter email and password";
    $("loginStatus").className = "status error";
    return;
  }

  $("loginBtn").disabled = true;
  $("loginBtn").textContent = "Signing in...";
  $("loginStatus").textContent = "";

  try {
    currentUser = await login(email, password);
    onLoggedIn();
  } catch (err) {
    $("loginStatus").textContent = err.message;
    $("loginStatus").className = "status error";
    $("loginBtn").disabled = false;
    $("loginBtn").textContent = "Sign In";
  }
});

$("signupBtn").addEventListener("click", async () => {
  const username = $("signupUsername").value.trim();
  const email = $("signupEmail").value.trim();
  const password = $("signupPassword").value;

  if (!username || !email || !password) {
    $("signupStatus").textContent = "All fields are required";
    $("signupStatus").className = "status error";
    return;
  }
  if (password.length < 6) {
    $("signupStatus").textContent = "Password must be at least 6 characters";
    $("signupStatus").className = "status error";
    return;
  }

  $("signupBtn").disabled = true;
  $("signupBtn").textContent = "Creating account...";
  $("signupStatus").textContent = "";

  try {
    const session = await signup(email, password, username);
    if (session) {
      currentUser = session;
      onLoggedIn();
    } else {
      $("signupStatus").textContent = "Check your email to confirm your account, then sign in.";
      $("signupStatus").className = "status success";
      $("signupBtn").disabled = false;
      $("signupBtn").textContent = "Create Account";
    }
  } catch (err) {
    $("signupStatus").textContent = err.message;
    $("signupStatus").className = "status error";
    $("signupBtn").disabled = false;
    $("signupBtn").textContent = "Create Account";
  }
});

$("showSignup").addEventListener("click", () => showView("signupView"));
$("showLogin").addEventListener("click", () => showView("loginView"));

$("userBadge").addEventListener("click", () => {
  if (confirm("Log out?")) logout();
});

// ─── Settings toggle ───

$("settingsToggle").addEventListener("click", () => {
  const panel = $("settingsPanel");
  panel.classList.toggle("open");
  $("settingsToggle").textContent = panel.classList.contains("open") ? "Hide settings" : "Settings";
});

["apiUrl", "topic", "autoExtract"].forEach((id) => {
  $(id).addEventListener("change", saveSettings);
  $(id).addEventListener("input", saveSettings);
});

// ─── Init ───

function onLoggedIn() {
  $("userBadge").textContent = currentUser.user_id;
  $("userBadge").style.display = "inline-block";
  loadSettings().then(extractArticle);
}

(async () => {
  const session = await loadSession();
  if (session) {
    currentUser = session;
    onLoggedIn();
  } else {
    showView("loginView");
  }
})();
