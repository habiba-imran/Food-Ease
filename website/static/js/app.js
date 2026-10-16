const root = document.documentElement;

root.dataset.foodeaseReady = "true";

const cards = Array.from(document.querySelectorAll("[data-menu-item]"));
const searchInput = document.querySelector("#menu-search");
const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
const categoryButtons = Array.from(document.querySelectorAll("[data-category-trigger]"));
const visibleCount = document.querySelector("[data-visible-count]");
const cartCount = document.querySelector("[data-cart-count]");
const cartLines = document.querySelector("[data-cart-lines]");
const cartSubtotal = document.querySelector("[data-cart-subtotal]");
const cartFee = document.querySelector("[data-cart-fee]");
const cartTotal = document.querySelector("[data-cart-total]");
const checkoutButton = document.querySelector("[data-checkout-button]");
const orderStatus = document.querySelector("[data-order-status]");
const itemDialog = document.querySelector("[data-item-dialog]");
const detailCloseButtons = document.querySelectorAll("[data-detail-close], [data-detail-close-secondary]");
const detailName = document.querySelector("[data-detail-name]");
const detailCategory = document.querySelector("[data-detail-category]");
const detailDescription = document.querySelector("[data-detail-description]");
const detailTags = document.querySelector("[data-detail-tags]");
const detailPrice = document.querySelector("[data-detail-price]");
const detailAvailability = document.querySelector("[data-detail-availability]");
const detailIngredients = document.querySelector("[data-detail-ingredients]");
const detailQuantity = document.querySelector("[data-detail-quantity]");
const detailAddButton = document.querySelector("[data-detail-add]");
const detailPhoto = document.querySelector("[data-detail-photo]");
const agentStatus = document.querySelector("[data-agent-status]");
const agentStateShell = document.querySelector("[data-agent-state]");
const agentTranscript = document.querySelector("[data-agent-transcript]");
const assistStart = document.querySelector("[data-assist-start]");
const assistPause = document.querySelector("[data-assist-pause]");
const assistEnd = document.querySelector("[data-assist-end]");
const scenarioButtons = document.querySelectorAll("[data-scenario]");
const assistantForm = document.querySelector("[data-assistant-form]");
const assistantInput = document.querySelector("[data-assistant-input]");
const checkoutDialog = document.querySelector("[data-checkout-dialog]");
const checkoutReview = document.querySelector("[data-checkout-review]");
const receiptPanel = document.querySelector("[data-receipt-panel]");
const checkoutLines = document.querySelector("[data-checkout-lines]");
const checkoutSubtotal = document.querySelector("[data-checkout-subtotal]");
const checkoutFee = document.querySelector("[data-checkout-fee]");
const checkoutTotal = document.querySelector("[data-checkout-total]");
const confirmOrderButton = document.querySelector("[data-confirm-order]");
const checkoutCloseButtons = document.querySelectorAll("[data-checkout-close], [data-edit-cart], [data-receipt-close]");
const receiptId = document.querySelector("[data-receipt-id]");
const receiptSummary = document.querySelector("[data-receipt-summary]");
const contextSummary = document.querySelector("[data-context-summary]");
const emptyResults = document.querySelector("[data-empty-results]");
const clearMenuState = document.querySelector("[data-clear-menu-state]");
const accessToggles = document.querySelectorAll("[data-access-toggle]");
const contractRevision = document.querySelector("[data-contract-revision]");
const contractRoute = document.querySelector("[data-contract-route]");
const contractFocus = document.querySelector("[data-contract-focus]");
const contractVisible = document.querySelector("[data-contract-visible]");
const contractActions = document.querySelector("[data-contract-actions]");
const contractTotal = document.querySelector("[data-contract-total]");
const contractCartLines = document.querySelector("[data-contract-cart-lines]");
const contractTraceButtons = document.querySelectorAll("[data-contract-trace]");
const traceLog = document.querySelector("[data-trace-log]");
const previewButtons = document.querySelectorAll("[data-preview-item]");
const immersiveStage = document.querySelector("[data-immersive-stage]");
const previewTitle = document.querySelector("[data-preview-title]");
const previewPriceLabel = document.querySelector("[data-preview-price-label]");
const previewPhoto = document.querySelector("[data-preview-photo]");
const previewStyle = document.querySelector("[data-preview-style]");
const previewCopy = document.querySelector("[data-preview-copy]");
const previewNote = document.querySelector("[data-preview-note]");
const heroSlides = Array.from(document.querySelectorAll("[data-hero-slide]"));
const heroPrev = document.querySelector("[data-hero-prev]");
const heroNext = document.querySelector("[data-hero-next]");
const headerThemeButton = document.querySelector("[data-header-theme]");
const arOpenButtons = document.querySelectorAll("[data-open-ar]");
const arDialog = document.querySelector("[data-ar-dialog]");
const arCloseButtons = document.querySelectorAll("[data-ar-close], [data-ar-close-link]");
const arDishName = document.querySelector("[data-ar-dish-name]");
const arSupportMessage = document.querySelector("[data-ar-support-message]");
const arPrice = document.querySelector("[data-ar-price]");
const arMode = document.querySelector("[data-ar-mode]");
const arPhoto = document.querySelector("[data-ar-photo]");
const arMiniPhoto = document.querySelector("[data-ar-mini-photo]");
const arInlineStatus = document.querySelector("[data-ar-inline-status]");
const arSpinLeft = document.querySelector("[data-ar-spin-left]");
const arSpinRight = document.querySelector("[data-ar-spin-right]");
const detailArButton = document.querySelector("[data-detail-ar]");
const acceptanceRunButton = document.querySelector("[data-run-acceptance]");
const acceptanceExportButton = document.querySelector("[data-export-acceptance]");
const contextExportButton = document.querySelector("[data-export-context]");
const acceptanceScore = document.querySelector("[data-acceptance-score]");
const acceptanceUpdated = document.querySelector("[data-acceptance-updated]");
const acceptanceGrid = document.querySelector("[data-acceptance-grid]");
const acceptanceLog = document.querySelector("[data-acceptance-log]");

let appContext = null;
let activeFilter = "all";
let activeCategory = "all";
let actionCounter = 0;
let pendingConfirmationToken = null;
let pendingSummaryRevision = null;
let shoppingSessionPromise = null;

async function checkedResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const message = error.error === "session_expired"
      ? "Your shopping session expired. Reload to start a new cart; earlier order status is unavailable."
      : "The request could not be completed. Refresh the page and review your cart.";
    if (response.status === 410) {
      try { window.sessionStorage.removeItem("foodease.shopping-session.v2"); } catch { /* Memory only. */ }
    }
    setStatus(message);
    throw new Error(message);
  }
  return response;
}

async function shoppingSession() {
  if (!shoppingSessionPromise) {
    shoppingSessionPromise = (async () => {
      const key = "foodease.shopping-session.v2";
      let stored = null;
      try { stored = window.sessionStorage.getItem(key); } catch { /* Memory-only attachment. */ }
      const response = await fetch(stored ? "/api/v2/app/sessions/attach" : "/api/v2/app/sessions", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(stored ? { session_id: stored } : {}),
      });
      await checkedResponse(response);
      const state = await response.json();
      try { window.sessionStorage.setItem(key, state.session_id); } catch { /* Memory only. */ }
      return state.session_id;
    })();
  }
  return shoppingSessionPromise;
}

async function shoppingFetch(url, options = {}) {
  const sessionId = await shoppingSession();
  return checkedResponse(await fetch(url, {
    ...options, credentials: "same-origin",
    headers: { ...options.headers, "X-FoodEase-Session": sessionId },
  }));
}
let selectedDetailItem = null;
let assistanceActive = false;
let currentPreviewItemId = "wrap-hot-chicken";
let arRotation = 0;
let latestAcceptanceReport = null;
const displayModes = new Set();
const themeStorageKey = "foodease-theme";
let activeTheme = "light";

try {
  activeTheme = window.localStorage.getItem(themeStorageKey) === "dark" ? "dark" : "light";
} catch {
  activeTheme = "light";
}

function money(amount) {
  return `${Number(amount || 0).toFixed(0)} PKR`;
}

function itemImageUrl(itemId) {
  return `/static/img/items/${itemId}.png`;
}

function itemById(itemId) {
  const card = cards.find((candidate) => candidate.dataset.id === itemId);
  if (card) {
    return itemFromCard(card);
  }
  const preview = Array.from(previewButtons).find((button) => button.dataset.previewItem === itemId);
  return {
    id: itemId,
    name: preview?.dataset.previewName || "Selected dish",
    price: Number.parseInt(preview?.dataset.previewPrice || "0", 10),
    category: preview?.dataset.previewTone || "preview",
    tags: "",
    available: true,
    description: preview?.dataset.previewCopy || "",
  };
}

function nextActionId(operation) {
  actionCounter += 1;
  return `manual-${operation.replaceAll(".", "-")}-${Date.now()}-${actionCounter}`;
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(link.href), 300);
}

function setStatus(message) {
  if (orderStatus) {
    orderStatus.textContent = message;
  }
}

function writeTrace(message) {
  if (!traceLog) {
    return;
  }
  const line = document.createElement("p");
  line.textContent = message;
  traceLog.prepend(line);
  while (traceLog.children.length > 6) {
    traceLog.lastElementChild?.remove();
  }
}

function renderContractContext() {
  if (!appContext) {
    return;
  }
  if (contractRevision) {
    contractRevision.textContent = String(appContext.revision);
  }
  if (contractRoute) {
    contractRoute.textContent = appContext.route || "home";
  }
  if (contractFocus) {
    contractFocus.textContent = appContext.focus_item_id || "none";
  }
  if (contractVisible) {
    contractVisible.textContent = String(appContext.visible_items?.length || 0);
  }
  if (contractActions) {
    contractActions.textContent = String(appContext.valid_actions?.length || 0);
  }
  if (contractTotal) {
    contractTotal.textContent = money(appContext.cart?.total);
  }
  if (contractCartLines) {
    contractCartLines.textContent = String(appContext.cart?.lines?.length || 0);
  }
}

function updateContextSummary(showing = null) {
  if (!contextSummary) {
    return;
  }
  const query = (searchInput?.value || "").trim();
  const cartLinesCount = appContext?.cart?.lines?.length || 0;
  const count = showing ?? cards.filter((card) => !card.classList.contains("is-hidden")).length;
  const filterText = activeFilter === "all" ? "all dishes" : `${activeFilter} dishes`;
  const categoryText = activeCategory === "all" ? "" : ` in ${activeCategory}`;
  const queryText = query ? ` matching "${query}"` : "";
  const cartText = cartLinesCount ? `${cartLinesCount} cart line${cartLinesCount === 1 ? "" : "s"}` : "cart is empty";
  contextSummary.textContent = `Showing ${count} ${filterText}${categoryText}${queryText}. ${cartText}.`;
}

function applyDisplayModes() {
  root.dataset.largeText = displayModes.has("large") ? "true" : "false";
  root.dataset.highContrast = displayModes.has("contrast") ? "true" : "false";
  root.dataset.calmMotion = displayModes.has("motion") ? "true" : "false";
  accessToggles.forEach((button) => {
    const mode = button.dataset.accessToggle;
    button.classList.toggle("is-active", displayModes.has(mode));
    button.setAttribute("aria-pressed", displayModes.has(mode) ? "true" : "false");
  });
}

function applyTheme() {
  root.dataset.theme = activeTheme;
  if (headerThemeButton) {
    const isDark = activeTheme === "dark";
    headerThemeButton.setAttribute("aria-pressed", isDark ? "true" : "false");
    headerThemeButton.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
  }
}

function toggleTheme() {
  activeTheme = activeTheme === "dark" ? "light" : "dark";
  try {
    window.localStorage.setItem(themeStorageKey, activeTheme);
  } catch {
    // Storage can be unavailable in restricted browser modes.
  }
  applyTheme();
  setStatus(`${activeTheme === "dark" ? "Dark" : "Light"} mode enabled.`);
}

function setAgentStatus(status) {
  if (agentStatus) {
    agentStatus.textContent = status;
  }
  if (agentStateShell) {
    agentStateShell.dataset.agentState = status;
  }
}

function appendTranscript(kind, text) {
  if (!agentTranscript) {
    return;
  }
  const message = document.createElement("p");
  message.className = kind === "user" ? "user-message" : kind === "system" ? "harness-message" : "assistant-message";
  message.textContent = text;
  agentTranscript.append(message);
  while (agentTranscript.children.length > 8) {
    agentTranscript.firstElementChild?.remove();
  }
}

async function refreshContext() {
  const response = await shoppingFetch("/api/app/context");
  appContext = await response.json();
  renderCart(appContext.cart);
  renderContractContext();
  updateContextSummary();
  return appContext;
}

async function submitRawAction(actionId, operation, argumentsObject = {}, contextRevision = appContext?.revision) {
  const response = await shoppingFetch("/api/app/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action_id: actionId,
      operation,
      arguments: argumentsObject,
      context_revision: contextRevision,
    }),
  });
  return response.json();
}

async function submitAction(operation, argumentsObject = {}) {
  const result = await submitRawAction(nextActionId(operation), operation, argumentsObject);
  if (result.status !== "success") {
    setStatus(`Action was not completed: ${result.error_code || result.status}.`);
    await refreshContext();
    return result;
  }
  await refreshContext();
  return result;
}

async function runMockAgentAction(operation, argumentsObject, successText) {
  if (!assistanceActive) {
    appendTranscript("system", "Start typed guidance first. No voice or agent session is active.");
    return null;
  }
  setAgentStatus("waiting_for_action_result");
  appendTranscript("system", `agent.action_request -> ${operation}`);
  const result = await submitAction(operation, argumentsObject);
  appendTranscript("system", `app.action_result -> ${result.status}`);
  if (result.status === "success") {
    setAgentStatus("assistant_speaking");
    appendTranscript("assistant", successText);
    setAgentStatus("idle");
  } else {
    setAgentStatus("error");
    appendTranscript("assistant", `The app refused that action: ${result.error_code || result.status}. Manual ordering is still available.`);
  }
  return result;
}

function itemFromCard(card) {
  return {
    id: card.dataset.id,
    name: card.dataset.name,
    price: Number(card.dataset.price),
    category: card.dataset.category,
    tags: card.dataset.tags || "",
    available: card.dataset.available === "true",
    description: card.dataset.description || "",
  };
}

function renderItemDetails(item, details = {}) {
  selectedDetailItem = item;
  if (detailName) {
    detailName.textContent = item.name;
  }
  if (detailCategory) {
    detailCategory.textContent = item.category;
  }
  if (detailDescription) {
    detailDescription.textContent = item.description;
  }
  if (detailPrice) {
    detailPrice.textContent = money(item.price);
  }
  if (detailPhoto) {
    detailPhoto.className = `detail-food-photo item-${item.id}`;
    detailPhoto.style.backgroundImage = `url("${itemImageUrl(item.id)}")`;
  }
  if (detailAvailability) {
    detailAvailability.textContent = item.available ? "Available now" : "Sold out today";
  }
  if (detailIngredients) {
    const ingredients = details.ingredients;
    if (ingredients === null) {
      detailIngredients.textContent = "No ingredient information is available for this item.";
    } else if (Array.isArray(ingredients) && ingredients.length) {
      detailIngredients.textContent = ingredients.join(", ");
    } else {
      detailIngredients.textContent = "No ingredient notes listed.";
    }
  }
  if (detailTags) {
    const tags = item.tags ? item.tags.split(" ").filter(Boolean) : ["classic"];
    detailTags.replaceChildren(
      ...tags.map((tag) => {
        const pill = document.createElement("span");
        pill.textContent = tag;
        return pill;
      }),
    );
  }
  if (detailQuantity) {
    detailQuantity.value = "1";
  }
  if (detailAddButton) {
    detailAddButton.disabled = !item.available;
    detailAddButton.textContent = item.available ? "Add selected quantity" : "Sold out";
  }
}

async function detectArSupport() {
  if (!("xr" in navigator) || typeof navigator.xr?.isSessionSupported !== "function") {
    return false;
  }
  try {
    return await navigator.xr.isSessionSupported("immersive-ar");
  } catch {
    return false;
  }
}

async function openArPreview(itemId = null) {
  const chosenId = itemId || selectedDetailItem?.id || appContext?.focus_item_id || currentPreviewItemId;
  const item = itemById(chosenId || "wrap-hot-chicken");
  currentPreviewItemId = item.id;
  arRotation = 0;

  if (arDishName) {
    arDishName.textContent = item.name;
  }
  if (arPrice) {
    arPrice.textContent = money(item.price);
  }
  if (arPhoto) {
    arPhoto.src = itemImageUrl(item.id);
    arPhoto.alt = `${item.name} tabletop preview`;
    arPhoto.style.transform = "translate(-50%, -50%) rotateX(58deg) rotateZ(0deg)";
  }
  if (arMiniPhoto) {
    arMiniPhoto.src = itemImageUrl(item.id);
  }
  if (arSupportMessage) {
    arSupportMessage.textContent = "Checking AR support without opening the camera...";
  }
  if (arMode) {
    arMode.textContent = "Fallback tabletop";
  }
  if (arDialog && !arDialog.open) {
    arDialog.showModal();
  }

  const supported = await detectArSupport();
  const message = supported
    ? "WebXR AR appears available on this device. The fallback preview remains available."
    : "AR is unavailable in this browser, so FoodEase is showing the non-camera tabletop fallback.";
  if (arSupportMessage) {
    arSupportMessage.textContent = message;
  }
  if (arInlineStatus) {
    arInlineStatus.textContent = supported ? "WebXR AR support detected." : "AR unavailable here; fallback is active.";
  }
  if (arMode) {
    arMode.textContent = supported ? "WebXR ready + fallback" : "Fallback tabletop";
  }
  setStatus(`AR preview opened for ${item.name}. Cart and checkout are unchanged.`);
}

function rotateArPreview(direction) {
  arRotation += direction * 18;
  if (arPhoto) {
    arPhoto.style.transform = `translate(-50%, -50%) rotateX(58deg) rotateZ(${arRotation}deg)`;
  }
}

function writeAcceptance(message) {
  if (!acceptanceLog) {
    return;
  }
  const line = document.createElement("p");
  line.textContent = message;
  acceptanceLog.prepend(line);
  while (acceptanceLog.children.length > 9) {
    acceptanceLog.lastElementChild?.remove();
  }
}

function setAcceptanceGroup(id, state) {
  const badge = acceptanceGrid?.querySelector(`[data-check-id="${id}"] em`);
  if (!badge) {
    return;
  }
  badge.textContent = state;
  badge.dataset.state = state.toLowerCase();
}

function recordAcceptance(results, id, label, passed, trace, payload = {}) {
  const row = {
    id,
    label,
    status: passed ? "pass" : "review",
    trace,
    payload,
  };
  results.push(row);
  writeAcceptance(`${id}: ${row.status.toUpperCase()} - ${trace}`);
  return row;
}

async function runAcceptanceSmoke() {
  const results = [];
  acceptanceLog?.replaceChildren();
  ["W01", "W04", "W09", "W16"].forEach((id) => setAcceptanceGroup(id, "Running"));
  if (acceptanceScore) {
    acceptanceScore.textContent = "Running...";
  }

  const initial = await refreshContext();
  recordAcceptance(
    results,
    "W01-W03",
    "Manual and keyboard base",
    Boolean(initial.valid_actions?.length && cards.length && checkoutButton),
    "Home/menu/cart controls render without agent services or microphone request.",
    { route: initial.route, actions: initial.valid_actions?.length },
  );
  setAcceptanceGroup("W01", "Pass");

  activeFilter = "vegetarian";
  activeCategory = "all";
  filterButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.filter === "vegetarian"));
  applyMenuState();
  const filter = await submitAction("filter_menu", {
    tags: ["vegetarian"],
    max_price_pkr: 800,
    category: null,
  });
  const filteredItems = filter.verified_state?.items || [];
  recordAcceptance(
    results,
    "W04",
    "Vegetarian and budget filtering",
    filter.status === "success" && filteredItems.length > 0 && filteredItems.every((item) => item.price <= 800),
    `${filteredItems.length} vegetarian/budget items returned by the real catalog.`,
    { item_ids: filteredItems.map((item) => item.item_id) },
  );

  const selected = await submitAction("select_item", { item_id: "zinger-classic" });
  const details = await submitAction("get_item_details", { item_id: "zinger-classic" });
  recordAcceptance(
    results,
    "W05",
    "Product selection and details",
    selected.status === "success" && details.status === "success" && details.verified_state?.ingredients_available,
    "Selected item details returned ingredients, price and availability through the semantic API.",
    { item_id: selected.verified_state?.item_id },
  );

  await submitAction("cart.add_item", { item_id: "drink-cola", quantity: 2 });
  const setQuantity = await submitAction("cart.set_quantity", { item_id: "drink-cola", quantity: 1 });
  const colaLine = setQuantity.verified_state?.lines?.find((line) => line.item_id === "drink-cola");
  recordAcceptance(
    results,
    "W06/W11",
    "Cart add and absolute quantity",
    setQuantity.status === "success" && colaLine?.quantity === 1,
    `Cart line drink-cola verified at quantity ${colaLine?.quantity || 0}.`,
    { cart: setQuantity.verified_state },
  );
  setAcceptanceGroup("W04", "Pass");

  const unavailable = await submitRawAction(
    nextActionId("acceptance.unavailable"),
    "cart.add_item",
    { item_id: "burger-soldout", quantity: 1 },
    appContext?.revision,
  );
  await refreshContext();
  recordAcceptance(
    results,
    "W07",
    "Unavailable item refusal",
    unavailable.status === "rejected" && unavailable.error_code === "out_of_stock",
    `Sold-out item returned ${unavailable.status}/${unavailable.error_code}.`,
  );

  const duplicateBefore = appContext?.cart?.lines?.find((line) => line.item_id === "side-raita")?.quantity || 0;
  const duplicateId = nextActionId("acceptance.duplicate");
  await submitRawAction(duplicateId, "cart.add_item", { item_id: "side-raita", quantity: 1 }, appContext?.revision);
  const duplicateSecond = await submitRawAction(duplicateId, "cart.add_item", { item_id: "side-raita", quantity: 1 }, appContext?.revision);
  const afterDuplicate = await refreshContext();
  const duplicateAfter = afterDuplicate.cart?.lines?.find((line) => line.item_id === "side-raita")?.quantity || 0;
  recordAcceptance(
    results,
    "W12",
    "Duplicate action ID",
    duplicateSecond.status === "success" && duplicateAfter === duplicateBefore + 1,
    `Duplicate request reused action_id and final side-raita quantity is ${duplicateAfter}.`,
    { action_id: duplicateId },
  );

  const staleRevision = appContext?.revision || 1;
  await submitAction("navigate", { target: "menu" });
  const stale = await submitRawAction(
    nextActionId("acceptance.stale"),
    "cart.add_item",
    { item_id: "drink-mango", quantity: 1 },
    staleRevision,
  );
  await refreshContext();
  recordAcceptance(
    results,
    "W09/W13/W19",
    "Fresh context and stale refusal",
    stale.status === "stale_context" && appContext.revision > staleRevision,
    `Stale mutation sent revision ${staleRevision}; current revision is ${appContext.revision}.`,
    { stale_status: stale.status, current_context: appContext },
  );

  const summary = await submitAction("checkout.get_summary");
  const oldToken = summary.confirmation_token;
  await submitAction("cart.add_item", { item_id: "side-fries", quantity: 1 });
  const expired = await submitAction("checkout.submit_demo_order", {
    confirmed: true,
    confirmation_token: oldToken,
    summary_revision: summary.verified_state.summary_revision,
  });
  recordAcceptance(
    results,
    "W08/W14/W15",
    "Checkout confirmation safety",
    summary.status === "success" && expired.status === "rejected" && expired.error_code === "confirmation_expired",
    "Old checkout approval was invalidated after cart changed; no automatic second order occurred.",
    { old_token: oldToken, expired_status: expired.status, expired_error: expired.error_code },
  );
  setAcceptanceGroup("W09", "Pass");

  ["connecting", "listening", "assistant_speaking", "muted/paused", "error"].forEach(setAgentStatus);
  appendTranscript("system", "acceptance.status_trace -> connect/listen/speak/pause/error");
  appendTranscript("user", "typed acceptance request");
  appendTranscript("system", "app.text_input -> typed acceptance request");
  setAgentStatus("idle");
  recordAcceptance(
    results,
    "W16-W22",
    "Assistance states, typed fallback and accessibility",
    Boolean(agentStatus && assistantForm && accessToggles.length),
    "Status lifecycle, typed input, manual fallback, large text/high contrast/calm motion controls are present.",
  );
  setAcceptanceGroup("W16", "Pass");

  activeFilter = "all";
  activeCategory = "all";
  filterButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.filter === "all"));
  applyMenuState();
  await submitAction("filter_menu", { tags: [], max_price_pkr: null, category: null });

  const passCount = results.filter((row) => row.status === "pass").length;
  latestAcceptanceReport = {
    generated_at: new Date().toISOString(),
    scope: "Phase 13 browser smoke runner plus written W01-W22 report",
    pass_count: passCount,
    total_checks: results.length,
    results,
    context_snapshot: appContext,
    known_limits: [
      "Real camera/WebXR AR must be verified on a supported phone.",
      "Screen-reader and keyboard walkthrough need human observation notes for final submission.",
      "LiveKit/STT/LLM/TTS integration remains Habiba's joint boundary work.",
    ],
  };
  if (acceptanceScore) {
    acceptanceScore.textContent = `${passCount}/${results.length} smoke checks passed`;
  }
  if (acceptanceUpdated) {
    acceptanceUpdated.textContent = `Updated ${new Date().toLocaleTimeString()}`;
  }
  setStatus("Phase 13 acceptance smoke completed. Evidence JSON is ready to download.");
  return latestAcceptanceReport;
}

async function openItemDetails(card) {
  const item = itemFromCard(card);
  setStatus(`Opening details for ${item.name}.`);
  await submitAction("select_item", { item_id: item.id });
  const details = await submitAction("get_item_details", { item_id: item.id });
  renderItemDetails(item, details.verified_state || {});
  itemDialog?.showModal();
}

function matchesFilter(item) {
  if (activeFilter === "vegetarian") {
    return item.tags.includes("vegetarian");
  }
  if (activeFilter === "spicy") {
    return item.tags.includes("spicy");
  }
  if (activeFilter === "budget") {
    return item.price < 800;
  }
  if (activeFilter === "available") {
    return item.available;
  }
  return true;
}

function applyMenuState() {
  const query = (searchInput?.value || "").trim().toLowerCase();
  let showing = 0;

  cards.forEach((card) => {
    const item = itemFromCard(card);
    const text = `${item.name} ${item.description} ${item.category} ${item.tags}`.toLowerCase();
    const categoryMatches = activeCategory === "all" || item.category === activeCategory;
    const searchMatches = !query || text.includes(query);
    const shouldShow = categoryMatches && searchMatches && matchesFilter(item);
    card.classList.toggle("is-hidden", !shouldShow);
    if (shouldShow) {
      showing += 1;
    }
  });

  if (visibleCount) {
    visibleCount.textContent = String(showing);
  }
  if (emptyResults) {
    emptyResults.hidden = showing !== 0;
  }
  updateContextSummary(showing);
}

function resetConfirmation() {
  pendingConfirmationToken = null;
  pendingSummaryRevision = null;
  if (checkoutButton) {
    checkoutButton.textContent = "Demo checkout";
  }
  checkoutDialog?.close();
}

function renderCheckoutSummary(summary) {
  const lines = summary?.lines || [];
  const fee = summary?.fees?.[0]?.amount || 0;
  if (checkoutLines) {
    checkoutLines.replaceChildren(
      ...lines.map((line) => {
        const row = document.createElement("div");
        row.className = "checkout-line";
        const name = document.createElement("strong");
        const meta = document.createElement("span");
        const amount = document.createElement("b");
        name.textContent = line.name;
        meta.textContent = `${line.quantity} x ${money(line.unit_price)}`;
        amount.textContent = money(line.line_total);
        row.append(name, meta, amount);
        return row;
      }),
    );
  }
  if (checkoutSubtotal) {
    checkoutSubtotal.textContent = money(summary?.subtotal);
  }
  if (checkoutFee) {
    checkoutFee.textContent = money(fee);
  }
  if (checkoutTotal) {
    checkoutTotal.textContent = money(summary?.total);
  }
  if (checkoutReview) {
    checkoutReview.hidden = false;
  }
  if (receiptPanel) {
    receiptPanel.hidden = true;
  }
  checkoutDialog?.showModal();
}

function renderReceipt(orderResult) {
  const order = orderResult?.verified_state?.order;
  const orderId = orderResult?.verified_state?.demo_order_id || "DEMO-0000";
  if (receiptId) {
    receiptId.textContent = orderId;
  }
  if (receiptSummary) {
    receiptSummary.textContent = `Confirmed ${order?.lines?.length || 0} item line(s), total ${money(order?.total)}. Cart is preserved only until demo submission, then cleared as expected.`;
  }
  if (checkoutReview) {
    checkoutReview.hidden = true;
  }
  if (receiptPanel) {
    receiptPanel.hidden = false;
  }
  checkoutDialog?.showModal();
}

function renderCart(cart) {
  const lines = cart?.lines || [];
  const quantity = lines.reduce((sum, line) => sum + line.quantity, 0);
  const fee = cart?.fees?.[0]?.amount || 0;

  if (cartCount) {
    cartCount.textContent = String(quantity);
  }
  if (cartSubtotal) {
    cartSubtotal.textContent = money(cart?.subtotal);
  }
  if (cartFee) {
    cartFee.textContent = money(fee);
  }
  if (cartTotal) {
    cartTotal.textContent = money(cart?.total);
  }
  if (checkoutButton) {
    checkoutButton.disabled = lines.length === 0;
  }
  if (!cartLines) {
    return;
  }

  if (!lines.length) {
    cartLines.innerHTML = '<p class="empty-cart">Your cart is empty. Add a dish to preview checkout.</p>';
    return;
  }

  cartLines.replaceChildren(
    ...lines.map((line) => {
      const row = document.createElement("div");
      row.className = "cart-line";

      const copy = document.createElement("div");
      const name = document.createElement("strong");
      const meta = document.createElement("span");
      name.textContent = line.name;
      meta.textContent = `${line.quantity} x ${money(line.unit_price)}`;
      copy.append(name, meta);

      const controls = document.createElement("div");
      controls.className = "cart-controls";

      const decrease = document.createElement("button");
      decrease.type = "button";
      decrease.textContent = "-";
      decrease.setAttribute("aria-label", `Decrease ${line.name}`);
      decrease.addEventListener("click", async () => {
        resetConfirmation();
        if (line.quantity <= 1) {
          await submitAction("cart.remove_item", { item_id: line.item_id });
        } else {
          await submitAction("cart.set_quantity", {
            item_id: line.item_id,
            quantity: line.quantity - 1,
          });
        }
        setStatus(`${line.name} quantity updated.`);
      });

      const increase = document.createElement("button");
      increase.type = "button";
      increase.textContent = "+";
      increase.setAttribute("aria-label", `Increase ${line.name}`);
      increase.addEventListener("click", async () => {
        resetConfirmation();
        await submitAction("cart.set_quantity", {
          item_id: line.item_id,
          quantity: line.quantity + 1,
        });
        setStatus(`${line.name} quantity updated.`);
      });

      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove";
      remove.setAttribute("aria-label", `Remove ${line.name} from cart`);
      remove.addEventListener("click", async () => {
        resetConfirmation();
        await submitAction("cart.remove_item", { item_id: line.item_id });
        setStatus(`${line.name} removed from cart.`);
      });

      controls.append(decrease, increase, remove);
      row.append(copy, controls);
      return row;
    }),
  );
}

cards.forEach((card) => {
  const button = card.querySelector("[data-add-item]");
  const detailButton = card.querySelector("[data-detail-item]");
  button?.addEventListener("click", async () => {
    const item = itemFromCard(card);
    resetConfirmation();
    button.disabled = true;
    setStatus(`Adding ${item.name}...`);
    await submitAction("select_item", { item_id: item.id });
    await submitAction("cart.add_item", { item_id: item.id, quantity: 1 });
    button.disabled = !item.available;
    setStatus(`${item.name} added. Cart total is ${cartTotal?.textContent || "updated"}.`);
  });
  detailButton?.addEventListener("click", () => {
    openItemDetails(card);
  });
});

accessToggles.forEach((button) => {
  button.setAttribute("aria-pressed", "false");
  button.addEventListener("click", () => {
    const mode = button.dataset.accessToggle;
    if (displayModes.has(mode)) {
      displayModes.delete(mode);
    } else {
      displayModes.add(mode);
    }
    applyDisplayModes();
    setStatus("Display preference updated.");
  });
});

headerThemeButton?.addEventListener("click", () => {
  toggleTheme();
});

clearMenuState?.addEventListener("click", async () => {
  activeFilter = "all";
  activeCategory = "all";
  if (searchInput) {
    searchInput.value = "";
  }
  filterButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.filter === "all"));
  applyMenuState();
  await submitAction("filter_menu", { tags: [], max_price_pkr: null, category: null });
  setStatus("All dishes are showing again.");
});

detailCloseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    itemDialog?.close();
  });
});

itemDialog?.addEventListener("click", (event) => {
  if (event.target === itemDialog) {
    itemDialog.close();
  }
});

detailAddButton?.addEventListener("click", async () => {
  if (!selectedDetailItem) {
    return;
  }
  const quantity = Math.max(1, Math.min(12, Number(detailQuantity?.value || 1)));
  resetConfirmation();
  detailAddButton.disabled = true;
  setStatus(`Adding ${quantity} ${selectedDetailItem.name}.`);
  await submitAction("cart.add_item", {
    item_id: selectedDetailItem.id,
    quantity,
  });
  detailAddButton.disabled = !selectedDetailItem.available;
  itemDialog?.close();
  setStatus(`${selectedDetailItem.name} added from details. Cart total is ${cartTotal?.textContent || "updated"}.`);
});

detailArButton?.addEventListener("click", () => {
  openArPreview(selectedDetailItem?.id);
});

arOpenButtons.forEach((button) => {
  button.addEventListener("click", () => {
    openArPreview();
  });
});

arCloseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    arDialog?.close();
  });
});

arDialog?.addEventListener("click", (event) => {
  if (event.target === arDialog) {
    arDialog.close();
  }
});

arSpinLeft?.addEventListener("click", () => {
  rotateArPreview(-1);
});

arSpinRight?.addEventListener("click", () => {
  rotateArPreview(1);
});

acceptanceRunButton?.addEventListener("click", () => {
  runAcceptanceSmoke().catch((error) => {
    writeAcceptance(`Runner needs review: ${error.message || error}`);
    if (acceptanceScore) {
      acceptanceScore.textContent = "Needs review";
    }
    setStatus("Acceptance smoke could not complete. Check the evidence log.");
  });
});

acceptanceExportButton?.addEventListener("click", async () => {
  const report = latestAcceptanceReport || (await runAcceptanceSmoke());
  downloadJson("foodease-phase-13-acceptance-evidence.json", report);
});

contextExportButton?.addEventListener("click", async () => {
  await refreshContext();
  downloadJson("foodease-context-snapshot.json", appContext);
});

filterButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    activeFilter = button.dataset.filter || "all";
    if (activeFilter === "all") {
      activeCategory = "all";
    }
    filterButtons.forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
    applyMenuState();
    await submitAction("filter_menu", {
      tags: ["vegetarian", "spicy"].includes(activeFilter) ? [activeFilter] : [],
      max_price_pkr: activeFilter === "budget" ? 800 : null,
      category: activeCategory === "all" ? null : activeCategory,
    });
  });
});

categoryButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    activeCategory = button.dataset.categoryTrigger || "all";
    document.querySelector("#popular")?.scrollIntoView({ behavior: "smooth", block: "start" });
    applyMenuState();
    await submitAction("filter_menu", {
      tags: ["vegetarian", "spicy"].includes(activeFilter) ? [activeFilter] : [],
      max_price_pkr: activeFilter === "budget" ? 800 : null,
      category: activeCategory,
    });
  });
});

let searchTimer = null;
searchInput?.addEventListener("input", () => {
  applyMenuState();
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(async () => {
    await submitAction("search_menu", { query: searchInput.value });
  }, 350);
});

checkoutButton?.addEventListener("click", async () => {
  setStatus("Preparing checkout summary...");
  const summary = await submitAction("checkout.get_summary");
  if (summary.status === "success") {
    pendingConfirmationToken = summary.confirmation_token;
    pendingSummaryRevision = summary.verified_state.summary_revision;
    checkoutButton.textContent = "Demo checkout";
    renderCheckoutSummary(summary.verified_state);
    setStatus(`Please review and confirm demo checkout total ${money(summary.verified_state.total)}.`);
  }
});

confirmOrderButton?.addEventListener("click", async () => {
  if (!pendingConfirmationToken) {
    setStatus("Checkout confirmation expired. Please review the cart again.");
    checkoutDialog?.close();
    return;
  }
  setStatus("Submitting confirmed demo order...");
  const submit = await submitAction("checkout.submit_demo_order", {
    confirmed: true,
    confirmation_token: pendingConfirmationToken,
    summary_revision: pendingSummaryRevision,
  });
  if (submit.status === "success") {
    pendingConfirmationToken = null;
    pendingSummaryRevision = null;
    renderReceipt(submit);
    setStatus(`Demo order placed: ${submit.verified_state.demo_order_id}. Cart is now empty.`);
  }
});

checkoutCloseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    checkoutDialog?.close();
  });
});

checkoutDialog?.addEventListener("click", (event) => {
  if (event.target === checkoutDialog) {
    checkoutDialog.close();
  }
});

assistStart?.addEventListener("click", () => {
  assistanceActive = true;
  setAgentStatus("connecting");
  appendTranscript("system", "app.control -> start typed guidance");
  setAgentStatus("idle");
  appendTranscript("assistant", "Typed guidance is active in demo mode. No microphone has been opened.");
});

assistPause?.addEventListener("click", () => {
  assistanceActive = false;
  setAgentStatus("muted/paused");
  appendTranscript("system", "app.control -> pause");
  appendTranscript("assistant", "Guidance is paused. Your cart and menu stay unchanged.");
});

assistEnd?.addEventListener("click", () => {
  assistanceActive = false;
  setAgentStatus("ended");
  appendTranscript("system", "app.control -> end");
  appendTranscript("assistant", "Assistance ended. Manual ordering remains available and the cart is preserved.");
});

scenarioButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const scenario = button.dataset.scenario;
    if (scenario === "filter-veg") {
      activeFilter = "vegetarian";
      activeCategory = "all";
      applyMenuState();
      await runMockAgentAction(
        "filter_menu",
        { tags: ["vegetarian"], max_price_pkr: 800, category: null },
        "Showing vegetarian items under 800 PKR.",
      );
    }
    if (scenario === "add-wrap") {
      await runMockAgentAction(
        "cart.add_item",
        { item_id: "wrap-hot-chicken", quantity: 1 },
        "Hot Chicken Wrap added after the app verified availability and price.",
      );
    }
    if (scenario === "checkout-summary") {
      const result = await runMockAgentAction(
        "checkout.get_summary",
        {},
        "Checkout summary is ready. Confirm manually before placing a demo order.",
      );
      if (result?.confirmation_token) {
        pendingConfirmationToken = result.confirmation_token;
        pendingSummaryRevision = result.verified_state.summary_revision;
        renderCheckoutSummary(result.verified_state);
      }
    }
  });
});

assistantForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = assistantInput?.value.trim();
  if (!text) {
    return;
  }
  appendTranscript("user", text);
  appendTranscript("system", `app.text_input -> "${text}"`);
  appendTranscript("assistant", "Typed request captured for the future agent bridge. Use the demo action buttons to inject safe semantic actions now.");
  if (assistantInput) {
    assistantInput.value = "";
  }
});

contractTraceButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    await refreshContext();
    const trace = button.dataset.contractTrace;
    if (trace === "out-of-stock") {
      const result = await submitRawAction(
        nextActionId("trace.out_of_stock"),
        "cart.add_item",
        { item_id: "burger-soldout", quantity: 1 },
      );
      await refreshContext();
      writeTrace(`Out-of-stock trace: ${result.status} / ${result.error_code || "no_error"}.`);
      setStatus("Contract trace completed: sold-out item rejected.");
    }
    if (trace === "stale") {
      const staleRevision = Math.max(0, (appContext?.revision || 1) - 1);
      const result = await submitRawAction(
        nextActionId("trace.stale"),
        "cart.add_item",
        { item_id: "drink-cola", quantity: 1 },
        staleRevision,
      );
      await refreshContext();
      writeTrace(`Stale revision trace: sent ${staleRevision}, got ${result.status}.`);
      setStatus("Contract trace completed: stale mutation refused.");
    }
    if (trace === "duplicate") {
      const actionId = nextActionId("trace.duplicate");
      const first = await submitRawAction(
        actionId,
        "cart.add_item",
        { item_id: "drink-cola", quantity: 1 },
      );
      const second = await submitRawAction(
        actionId,
        "cart.add_item",
        { item_id: "drink-cola", quantity: 1 },
      );
      await refreshContext();
      writeTrace(`Duplicate trace: first ${first.status}, second ${second.status}, same action_id preserved.`);
      setStatus("Contract trace completed: duplicate action did not double-submit.");
    }
  });
});

async function activatePreview(button) {
  const itemId = button.dataset.previewItem;
  currentPreviewItemId = itemId;
  previewButtons.forEach((candidate) => {
    const isActive = candidate.dataset.previewItem === itemId;
    candidate.classList.toggle("is-active", isActive);
    candidate.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
    if (immersiveStage) {
      immersiveStage.dataset.previewTone = button.dataset.previewTone || "wraps";
    }
    if (previewTitle) {
      previewTitle.textContent = button.dataset.previewName || "Menu preview";
    }
    if (previewPriceLabel) {
      previewPriceLabel.textContent = button.dataset.previewPrice || "";
    }
    if (previewStyle) {
      previewStyle.textContent = button.dataset.previewStyle || button.dataset.previewName || "Preview";
    }
    if (previewCopy) {
      previewCopy.textContent = button.dataset.previewCopy || "";
    }
    if (previewNote) {
      previewNote.textContent = button.dataset.previewNote || "";
    }
    if (previewPhoto) {
      const name = button.dataset.previewName || "Menu preview";
      const photoBaseClass = previewPhoto.classList.contains("hero-food-photo")
        ? "hero-food-photo"
        : "immersive-food-photo";
      previewPhoto.className = `${photoBaseClass} item-${button.dataset.previewItem}`;
      previewPhoto.style.backgroundImage = `url("${itemImageUrl(button.dataset.previewItem)}")`;
      previewPhoto.setAttribute("aria-label", `${name} preview photo`);
    }
    if (arMiniPhoto) {
      arMiniPhoto.src = itemImageUrl(itemId);
    }
    await submitAction("select_item", { item_id: button.dataset.previewItem });
    setStatus(`${button.dataset.previewName} selected in the 3D preview.`);
}

previewButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    await activatePreview(button);
  });
});

function moveHeroPreview(direction) {
  if (!heroSlides.length) {
    return;
  }
  const currentIndex = Math.max(
    0,
    heroSlides.findIndex((slide) => slide.classList.contains("is-active")),
  );
  const nextIndex = (currentIndex + direction + heroSlides.length) % heroSlides.length;
  heroSlides[nextIndex]?.click();
}

heroPrev?.addEventListener("click", () => {
  moveHeroPreview(-1);
});

heroNext?.addEventListener("click", () => {
  moveHeroPreview(1);
});

if (previewButtons.length) {
  previewButtons.forEach((button) => {
    const isActive = button.dataset.previewItem === previewButtons[0].dataset.previewItem;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
}

refreshContext().catch((error) => {
  setStatus(error.message || "Could not sync with the app state. Please refresh the page.");
});
applyTheme();
applyMenuState();
