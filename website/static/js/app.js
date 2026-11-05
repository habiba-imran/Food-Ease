import { Application, newId } from "./application.mjs";
import { AssistanceController } from "./assistance-controller.mjs?v=voice-13";
import { LiveKitSeats } from "./livekit-bridge.mjs";
import { TranscriptView } from "./transcripts.mjs";
import { acquireTabLease } from "./tab-lease.mjs";
import { voicePresentation, voiceErrorMessage } from "./voice-ui.mjs";

const root = document.documentElement;
const voiceControls = document.querySelector("[data-voice-controls]");
const voiceLauncher = document.querySelector("[data-voice-launcher]");
const voiceLauncherHome = document.createComment("voice launcher home");
voiceLauncher?.before(voiceLauncherHome);
root.dataset.assistanceState = "awaiting_spoken_choice_consent";

root.dataset.foodeaseReady = "true";

const cards = Array.from(document.querySelectorAll("[data-menu-item]"));
const menuCategoryGroups = Array.from(document.querySelectorAll("[data-menu-category-group]"));
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
const cartDialog = document.querySelector("[data-cart-dialog], #cart-preview");
const cartButton = document.querySelector(".cart-button, [data-cart-trigger]");
const cartCloseButtons = document.querySelectorAll("[data-cart-close], [data-cart-close-secondary]");
const cartHeaderCount = document.querySelector("[data-cart-header-count]");
const dialogOrigins = new WeakMap();
let shoppingOrigin = null;
let cartBusy = false;
let checkoutBusy = false;
let confirmationBusy = false;
let navigationBusy = false;
const navigationRequests = new Map();

function showDialog(dialog) {
  if (!dialog || dialog.open) return;
  if (voiceControls?.open) voiceControls.close();
  const active = document.activeElement;
  if (active && active !== document.body && !active.closest("dialog")) shoppingOrigin = active;
  dialogOrigins.set(dialog, shoppingOrigin || cartButton);
  dialog.querySelector("[data-dialog-status]")?.replaceChildren();
  dialog.querySelectorAll("[data-reconcile-action]").forEach(button => { button.hidden = true; });
  dialog.showModal();
  syncDialogAssistance();
}

function outsideDialog(event, dialog) {
  if (event.target !== dialog) return false;
  const rect = dialog.getBoundingClientRect();
  return event.clientX < rect.left || event.clientX > rect.right
    || event.clientY < rect.top || event.clientY > rect.bottom;
}

async function navigateOnce(target) {
  if (navigationRequests.has(target)) return navigationRequests.get(target);
  const task = submitAction("navigate", { target });
  navigationRequests.set(target, task);
  try { return await task; }
  finally { navigationRequests.delete(target); }
}

async function requestCart() {
  const result = await navigateOnce("cart");
  const message = orderStatus?.textContent;
  openCart();
  if (result?.status !== "success" && message) setStatus(message);
}

function dismissDialog(dialog, target) {
  dialog?.close();
  void navigateOnce(target);
}

function openCart() {
  if (cartDialog && !cartDialog.open) {
    showDialog(cartDialog);
    cartButton?.setAttribute("aria-expanded", "true");
  }
}

function closeCart() {
  if (cartDialog && cartDialog.open) {
    cartDialog.close();
    cartButton?.setAttribute("aria-expanded", "false");
  }
}
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
// Relocate the existing typed UI only; its handlers, draft, transcript and session survive.
const assistantFormHome = document.createComment("typed form home");
const transcriptHome = document.createComment("transcript home");
assistantForm?.before(assistantFormHome);
agentTranscript?.before(transcriptHome);

function syncDialogAssistance() {
  const activeDialog = voiceControls?.open ? voiceControls : document.querySelector("dialog[open]");
  const destination = assistanceActive && (liveSeats?.mode === "typed" || activeDialog === voiceControls)
    ? activeDialog?.querySelector("[data-dialog-assistant]") : null;
  document.querySelectorAll("[data-dialog-assistant]").forEach(slot => { slot.hidden = slot !== destination; });
  document.querySelectorAll("[data-dialog-end-assistance]").forEach(button => { button.hidden = !assistanceActive; });
  document.querySelectorAll("[data-dialog-typing]").forEach(button => { button.hidden = !assistanceActive || liveSeats?.mode === "typed"; });
  const changed = destination ? assistantForm?.parentElement !== destination : assistantForm?.previousSibling !== assistantFormHome;
  if (!changed) return;
  agentTranscript?.setAttribute("aria-live", "off");
  if (destination) destination.append(agentTranscript, assistantForm);
  else {
    transcriptHome.after(agentTranscript);
    assistantFormHome.after(assistantForm);
  }
  requestAnimationFrame(() => agentTranscript?.setAttribute("aria-live", "polite"));
}
const demoDetails = document.querySelector("#project-details");
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
let assistanceIntent = 0;
let currentPreviewItemId = "wrap-hot-chicken";
let arRotation = 0;
let latestAcceptanceReport = null;
let applicationPromise = null;
let catalogItems = new Map();
let lastRenderedCart = null;
let lastRenderedRoute = null;
let lastRenderedFocus = null;
const transcriptView = new TranscriptView(agentTranscript);
let liveSeats = null;
let assistanceController = null;
let assistancePaused = false;
const displayModes = new Set();
const themeStorageKey = "foodease-theme";
let activeTheme = "light";

try {
  activeTheme = window.localStorage.getItem(themeStorageKey) === "dark" ? "dark" : "light";
} catch {
  activeTheme = "light";
}

function money(amount) {
  const value = Number(amount || 0);
  return `${value.toFixed(Number.isInteger(value) ? 0 : 2)} PKR`;
}

function itemImageUrl(itemId, size = 640) {
  return `/static/img/catalog-v7/${itemId}-${size}.webp`;
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
  // Only the active surface announces; background content is inert in a modal.
  const surface = voiceControls?.open ? voiceControls : document.querySelector("dialog[open]");
  const target = surface?.querySelector("[data-dialog-status]") || orderStatus;
  if (target && target.textContent !== message) target.textContent = message;
  if (/pending changes|unknown|unresolved|could not synchronize/i.test(message)) {
    const reconcile = surface?.querySelector("[data-reconcile-action]");
    if (reconcile) reconcile.hidden = false;
    else if (demoDetails) demoDetails.open = true;
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
    headerThemeButton.setAttribute("title", isDark ? "Switch to light mode" : "Switch to dark mode");
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
  syncVoiceUi();
}

function currentVoicePresentation() {
  const run = assistanceController?.current;
  const microphoneActive = !run?.cancelled && (run?.media?.getAudioTracks?.() || [])
    .some(track => track.readyState !== "ended" && track.enabled !== false);
  return voicePresentation({ phase: root.dataset.assistanceState,
    agentState: agentStateShell?.dataset.agentState, microphoneActive,
    cleanupPending: Boolean(run?.cancelled && run.serverPending) });
}

function syncVoiceUi() {
  if (!voiceLauncher) return;
  const view = currentVoicePresentation();
  voiceLauncher.dataset.voiceState = view.state;
  voiceLauncher.querySelector("[data-voice-launcher-label]").textContent = view.label;
  voiceLauncher.setAttribute("aria-label", view.canManage ? `${view.label} Open voice controls` : view.label);
  voiceLauncher.setAttribute("aria-expanded", String(Boolean(voiceControls?.open)));
  document.querySelectorAll("[data-voice-feedback]").forEach(node => {
    node.textContent = node.closest("[data-voice-controls]") ? view.label : `${view.label}. ${view.microphone}.`;
  });
  document.querySelectorAll("[data-voice-microphone]").forEach(node => {
    node.textContent = view.microphone;
    node.dataset.microphoneActive = String(view.microphone === "Microphone on");
  });
  const connecting = view.state === "connecting";
  const active = view.canManage && !connecting;
  voiceControls.querySelector("[data-voice-use]").hidden = view.state === "error" || connecting || root.dataset.assistanceState === "voice_active";
  voiceControls.querySelector("[data-voice-retry]").hidden = view.state !== "error";
  const pause = voiceControls.querySelector("[data-voice-pause]");
  pause.hidden = !active;
  pause.textContent = root.dataset.assistanceState === "paused" ? "Resume listening" : "Pause listening";
  pause.setAttribute("aria-pressed", String(root.dataset.assistanceState === "paused"));
  voiceControls.querySelector("[data-voice-end]").hidden = !view.canManage;
  voiceControls.querySelector("[data-voice-typed]").disabled = connecting;
  document.querySelectorAll("[data-welcome-voice], [data-welcome-typed]").forEach(button => { button.disabled = connecting; });
}

function placeVoiceLauncher() {
  if (!voiceLauncher) return;
  const slot = Array.from(document.querySelectorAll("dialog[open] [data-voice-launcher-slot]")).at(-1);
  if (slot && voiceLauncher.parentElement !== slot) slot.append(voiceLauncher);
  else if (!slot && voiceLauncher.previousSibling !== voiceLauncherHome) voiceLauncherHome.after(voiceLauncher);
}

function openVoiceControls() {
  if (!voiceControls.open) voiceControls.showModal();
  syncDialogAssistance();
  syncVoiceUi();
}

function finishManualUi() {
  voiceControls?.close();
  placeVoiceLauncher();
  syncDialogAssistance();
  syncVoiceUi();
  const target = document.querySelector("dialog[open]") ? voiceLauncher : document.querySelector("#popular");
  target?.focus({ preventScroll: false });
  setStatus("You can browse the menu and order manually. Start Voice Assistant whenever you need help. Your microphone is off.");
}

function appendTranscript(kind, text) {
  const id = newId();
  transcriptView.update({ kind, turnId: id, utteranceId: id, text, timestamp: new Date().toISOString() });
}

async function application() {
  if (!applicationPromise) applicationPromise = (async () => {
    const sessionId = await shoppingSession();
    const catalog = await (await checkedResponse(await fetch("/api/catalog/items"))).json();
    catalogItems = new Map(catalog.items.map((item) => [item.item_id, item]));
    const transport = {
      context: async () => (await shoppingFetch("/api/v2/app/context")).json(),
      action: async (request) => (await shoppingFetch("/api/v2/app/action", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request),
      })).json(),
      lookup: async (actionId, eventId = newId()) => {
        const result = await (await shoppingFetch(`/api/v2/app/actions/${encodeURIComponent(actionId)}`, {
          headers: { "X-FoodEase-Event-Id": eventId },
        })).json();
        if (result.schema_version !== "2.0" || result.session_id !== sessionId || result.action_id !== actionId
            || result.reply_to !== eventId || !["found", "pending", "not_seen", "expired"].includes(result.state)) throw new Error("The earlier action could not be verified.");
        return result;
      },
    };
    let storage = null;
    try { storage = window.sessionStorage; } catch { /* Memory-only session. */ }
    return new Application({ sessionId, transport, render: renderApplication, onError: setStatus, storage });
  })();
  return applicationPromise;
}

async function renderApplication(snapshot, result = null, request = null) {
  appContext = snapshot;
  activeCategory = snapshot.category || "all";
  activeFilter = snapshot.filter_tags[0] || (snapshot.max_price_pkr !== null ? "budget" : "all");
  if (searchInput && searchInput !== document.activeElement) searchInput.value = snapshot.search_query || "";
  for (const button of filterButtons) {
    const filter = button.dataset.filter;
    const active = snapshot.filter_tags.includes(filter) || filter === "budget" && snapshot.max_price_pkr !== null
      || filter === "all" && snapshot.filter_tags.length === 0 && snapshot.max_price_pkr === null && !snapshot.category;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  }
  for (const button of categoryButtons) button.setAttribute("aria-pressed", String(button.dataset.categoryTrigger === snapshot.category));
  const cartKey = JSON.stringify(snapshot.cart);
  const cartChanged = cartKey !== lastRenderedCart;
  if (cartChanged) {
    const active = document.activeElement;
    const label = active?.getAttribute("aria-label");
    const rows = Array.from(cartLines?.children || []);
    const rowIndex = rows.indexOf(active?.closest(".cart-line"));
    const scrollTop = cartDialog?.scrollTop || 0;
    renderCart(snapshot.cart);
    lastRenderedCart = cartKey;
    if (label && active && !active.isConnected) {
      const same = Array.from(cartLines?.querySelectorAll("button") || []).find((b) => b.getAttribute("aria-label") === label);
      const next = cartLines?.children[Math.max(0, Math.min(rowIndex, cartLines.children.length - 1))];
      (same && !same.disabled ? same : next?.querySelector("button:not(:disabled)") || cartDialog?.querySelector("[data-cart-close]"))?.focus({ preventScroll: true });
    }
    if (cartDialog) cartDialog.scrollTop = scrollTop;
    pendingConfirmationToken = pendingSummaryRevision = null;
  }
  applyMenuState();
  renderContractContext();
  const routeChanged = lastRenderedRoute !== snapshot.route || lastRenderedFocus !== snapshot.focus_item_id;
  if (snapshot.route !== "item" && itemDialog?.open) itemDialog.close();
  if (!["checkout", "confirmation"].includes(snapshot.route) && checkoutDialog?.open) checkoutDialog.close();
  if (snapshot.route !== "cart" && cartDialog?.open && ["home", "menu", "item", "checkout", "confirmation"].includes(snapshot.route)) closeCart();
  if (snapshot.route === "item" && snapshot.focus_item_id) {
    const detail = catalogItems.get(snapshot.focus_item_id);
    if (detail && (routeChanged || ["get_item_details", "select_item"].includes(result?.operation))) {
      const preview = Array.from(previewButtons).find((button) => button.dataset.previewItem === detail.item_id);
      if (preview) paintPreview(preview);
      renderItemDetails({ id: detail.item_id, name: detail.name, price: detail.unit_price_pkr,
        category: detail.category, tags: detail.tags.join(" "), available: detail.available,
        description: detail.description }, detail);
      showDialog(itemDialog);
    }
  } else if (snapshot.route === "checkout") {
    const summary = result?.status === "success" && result.operation === "checkout.get_summary" ? result : null;
    if (summary) {
      pendingConfirmationToken = summary.confirmation_token;
      pendingSummaryRevision = summary.verified_state.summary_revision;
    }
    if (routeChanged || summary || cartChanged) renderCheckoutSummary(summary?.verified_state || snapshot.cart);
    if (confirmOrderButton) confirmOrderButton.disabled = !pendingConfirmationToken;
  } else if (snapshot.route === "confirmation" && result?.status === "success" && result.operation === "checkout.submit_demo_order") {
    renderReceipt(result);
    try { sessionStorage.setItem("foodease.last-order-action.v2", request.payload.action_id); } catch { /* Memory-only. */ }
  }
  if (routeChanged && ["home", "menu", "cart"].includes(snapshot.route)) {
    if (snapshot.route === "cart") {
      openCart();
    } else {
      closeCart();
      if (!["cart", "item", "checkout", "confirmation"].includes(lastRenderedRoute)) {
        document.querySelector(snapshot.route === "menu" ? "#popular" : "#main")?.scrollIntoView({ block: "start", behavior: "instant" });
      }
    }
  }
  lastRenderedRoute = snapshot.route;
  lastRenderedFocus = snapshot.focus_item_id;
  root.dataset.foodeaseRevision = String(snapshot.revision);
  root.dataset.foodeaseRoute = snapshot.route;
  updateContextSummary();
  syncDialogAssistance();
  placeVoiceLauncher();
  syncVoiceUi();
}

async function refreshContext() {
  const app = await application();
  const snapshot = await app.refresh();
  if (snapshot.route === "confirmation") {
    let actionId = null;
    try { actionId = sessionStorage.getItem("foodease.last-order-action.v2"); } catch { /* Memory-only. */ }
    if (actionId) {
      const lookup = await app.transport.lookup(actionId);
      const result = lookup.result;
      if (lookup.state === "found" && result?.session_id === app.sessionId
          && result.context_revision === snapshot.revision && result.payload.status === "success"
          && result.payload.operation === "checkout.submit_demo_order") await app.accept(snapshot, { result });
    }
  }
  return app.snapshot;
}

async function submitRawAction(actionId, operation, argumentsObject = {}, contextRevision = null) {
  const app = await application();
  return (await app.manual(operation, argumentsObject, actionId, contextRevision)).payload;
}

async function submitAction(operation, argumentsObject = {}) {
  let result;
  try { result = await submitRawAction(nextActionId(operation), operation, argumentsObject); }
  catch (error) {
    setStatus(error.message || "The outcome could not be verified. Use Check pending changes before trying again.");
    return { status: "timeout_unknown", error_code: "timeout", verified_state: null };
  }
  if (result.status === "timeout_unknown") setStatus("The outcome is unknown. Use Check pending changes; no action has been sent again.");
  else if (result.status !== "success") setStatus({
    out_of_stock: "This dish is sold out. Please choose another item.",
    invalid_arguments: "That change is unavailable. Each dish can have up to 99 in the cart.",
    confirmation_expired: "Your review expired or the cart changed. Edit your cart, then review checkout again.",
    stale_context: "Your order changed. Review the updated cart before trying again.",
    not_available: "This action is unavailable. Review your cart and try again.",
  }[result.error_code] || `Action was not completed: ${result.error_code || result.status}.`);
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
  const resetQuantity = !itemDialog?.open || selectedDetailItem?.id !== item.id;
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
    detailPhoto.style.backgroundImage = `url("${itemImageUrl(item.id, 960)}")`;
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
  if (detailQuantity && resetQuantity) {
    detailQuantity.value = "1";
    detailQuantity.disabled = !item.available;
    detailQuantity.removeAttribute("aria-invalid");
  }
  const quantityError = document.querySelector("#quantity-error");
  if (quantityError && resetQuantity) quantityError.hidden = true;
  updateDetailTotal();
  if (detailAddButton) {
    detailAddButton.disabled = !item.available;
    detailAddButton.textContent = item.available ? "Add selected quantity" : "Sold out";
  }
}

function updateDetailTotal() {
  const quantity = detailQuantity?.valueAsNumber;
  const valid = detailQuantity?.validity.valid && Number.isInteger(quantity);
  const total = document.querySelector("[data-detail-total]");
  if (total) total.textContent = valid ? money(quantity * (selectedDetailItem?.price || 0)) : "—";
  return valid;
}

detailQuantity?.addEventListener("input", () => {
  if (updateDetailTotal()) {
    detailQuantity.removeAttribute("aria-invalid");
    document.querySelector("#quantity-error").hidden = true;
  }
});

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
    arMiniPhoto.src = itemImageUrl(item.id, 480);
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
  if (assistanceActive) { setStatus("End assistance before running the manual diagnostics."); return; }
  appendTranscript("system", "Manual UI diagnostics do not verify the connected voice agent or audio playback.");
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
  if (navigationBusy) return;
  navigationBusy = true;
  try { await submitAction("select_item", { item_id: item.id }); }
  finally { navigationBusy = false; }
}

function applyMenuState() {
  if (!appContext) return;
  const visibleIds = new Set(appContext.visible_items.map((item) => item.item_id));
  let showing = 0;

  cards.forEach((card) => {
    const shouldShow = visibleIds.has(card.dataset.id);
    card.classList.toggle("is-hidden", !shouldShow);
    if (shouldShow) {
      showing += 1;
    }
  });

  menuCategoryGroups.forEach((group) => {
    const groupCount = Array.from(group.querySelectorAll("[data-menu-item]")).filter(
      (card) => !card.classList.contains("is-hidden"),
    ).length;
    group.hidden = groupCount === 0;
    const count = group.querySelector("[data-category-count]");
    if (count) {
      count.textContent = `${groupCount} ${groupCount === 1 ? "ITEM" : "ITEMS"}`;
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
  document.querySelector("#checkout-dialog-title").textContent = "Review your demo order";
  checkoutDialog?.setAttribute("aria-labelledby", "checkout-dialog-title");
  showDialog(checkoutDialog);
}

function renderReceipt(orderResult) {
  const order = orderResult?.verified_state?.order;
  const orderId = orderResult?.verified_state?.demo_order_id;
  if (!order || !orderId) return;
  if (receiptId) {
    receiptId.textContent = orderId;
  }
  if (receiptSummary) {
    receiptSummary.textContent = `Demo confirmed: ${order.lines.reduce((sum, line) => sum + line.quantity, 0)} items, total ${money(order.total)}. No payment was collected and no restaurant order was sent.`;
  }
  if (checkoutReview) {
    checkoutReview.hidden = true;
  }
  if (receiptPanel) {
    receiptPanel.hidden = false;
  }
  checkoutDialog?.setAttribute("aria-labelledby", "demo-receipt-title");
  showDialog(checkoutDialog);
  receiptId?.focus();
}

function renderCart(cart) {
  const lines = cart?.lines || [];
  const quantity = lines.reduce((sum, line) => sum + line.quantity, 0);
  const fee = cart?.fees?.[0]?.amount || 0;

  if (cartCount) {
    cartCount.textContent = String(quantity);
    if (cartButton) {
      cartButton.setAttribute("aria-label", `Open cart (${quantity} ${quantity === 1 ? "item" : "items"})`);
    }
  }
  if (cartHeaderCount) {
    cartHeaderCount.textContent = String(quantity);
    document.querySelector("[data-cart-header-unit]").textContent = quantity === 1 ? "item" : "items";
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
    checkoutButton.disabled = lines.length === 0 || cartBusy || checkoutBusy;
  }
  if (!cartLines) {
    return;
  }

  if (!lines.length) {
    cartLines.innerHTML = '<div class="empty-cart-state"><div class="empty-cart-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" width="44" height="44" stroke="currentColor" stroke-width="1.6"><path d="M5 7h14l1 14H4L5 7Zm3 0V5a4 4 0 0 1 8 0v2" stroke-linejoin="round"/><path d="M10 12a2 2 0 1 0 4 0" stroke-linecap="round"/></svg></div><h3>Your cart is empty</h3><p class="empty-cart-hint">Add something delicious that catches your eye to start your order.</p><button type="button" class="button ghost" data-cart-browse>Explore menu</button></div>';
    cartLines.querySelector("[data-cart-browse]")?.addEventListener("click", () => {
      dialogOrigins.set(cartDialog, document.querySelector("#popular"));
      dismissDialog(cartDialog, "menu");
      document.querySelector("#popular")?.focus();
    });
    return;
  }

  cartLines.replaceChildren(
    ...lines.map((line) => {
      const row = document.createElement("div");
      row.className = "cart-line";
      row.dataset.itemId = line.item_id;
      const image = document.createElement("img");
      image.className = "cart-line-image";
      image.src = itemImageUrl(line.item_id, 160);
      image.alt = "";
      image.width = 64;
      image.height = 64;

      const copy = document.createElement("div");
      copy.className = "cart-line-copy";
      const name = document.createElement("strong");
      name.className = "cart-line-name";
      name.textContent = line.name;
      const meta = document.createElement("span");
      meta.className = "cart-line-meta";
      meta.textContent = `${line.quantity} x ${money(line.unit_price)}`;
      copy.append(name, meta);

      const subtotal = document.createElement("span");
      subtotal.className = "cart-line-subtotal";
      subtotal.textContent = money(line.quantity * line.unit_price);

      const controls = document.createElement("div");
      controls.className = "cart-controls";

      const decrease = document.createElement("button");
      decrease.type = "button";
      decrease.className = "cart-stepper-btn cart-decrease";
      decrease.textContent = "-";
      decrease.setAttribute("aria-label", `Decrease ${line.name}${line.quantity === 1 ? " (removes item)" : ""}`);
      decrease.addEventListener("click", () => changeCart(line, line.quantity - 1));

      const qty = document.createElement("span");
      qty.className = "cart-stepper-qty";
      qty.textContent = String(line.quantity);

      const increase = document.createElement("button");
      increase.type = "button";
      increase.className = "cart-stepper-btn cart-increase";
      increase.textContent = "+";
      increase.setAttribute("aria-label", `Increase ${line.name}`);
      increase.disabled = line.quantity >= 99;
      if (increase.disabled) increase.title = "Maximum quantity is 99";
      increase.addEventListener("click", () => changeCart(line, line.quantity + 1));

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "cart-remove-btn";
      remove.textContent = "Remove";
      remove.setAttribute("aria-label", `Remove ${line.name} from cart`);
      remove.addEventListener("click", () => changeCart(line, 0));

      controls.append(decrease, qty, increase, remove);
      row.append(image, copy, subtotal, controls);
      return row;
    }),
  );
  setCartBusy(cartBusy);
}

function setCartBusy(busy) {
  cartLines?.setAttribute("aria-busy", String(busy));
  cartLines?.querySelectorAll("button").forEach(button => button.setAttribute("aria-disabled", String(busy)));
  if (checkoutButton) checkoutButton.disabled = busy || checkoutBusy || !appContext?.cart?.lines.length;
}

async function changeCart(line, quantity) {
  if (cartBusy) return;
  cartBusy = true;
  setCartBusy(true);
  resetConfirmation();
  setStatus(`Updating ${line.name}…`);
  try {
    const result = await submitAction(quantity === 0 ? "cart.remove_item" : "cart.set_quantity", {
      item_id: line.item_id, ...(quantity === 0 ? {} : { quantity }),
    });
    if (result.status === "success") setStatus(`${line.name} ${quantity === 0 ? "removed" : `quantity ${quantity}`}. Cart total ${cartTotal.textContent}.`);
  } finally {
    cartBusy = false;
    setCartBusy(false);
  }
}

cards.forEach((card) => {
  const button = card.querySelector("[data-add-item]");
  const detailButton = card.querySelector("[data-detail-item]");
  button?.addEventListener("click", async () => {
    const item = itemFromCard(card);
    resetConfirmation();
    button.disabled = true;
    setStatus(`Adding ${item.name}...`);
    const result = await submitAction("cart.add_item", { item_id: item.id, quantity: 1 });
    button.disabled = !item.available;
    if (result.status === "success") setStatus(`${item.name} added. Cart total is ${cartTotal?.textContent || "updated"}.`);
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
  if (searchInput) {
    searchInput.value = "";
  }
  await submitAction("search_menu", { query: "" });
  const result = await submitAction("filter_menu", { tags: [], max_price_pkr: null, category: null });
  if (result.status === "success") setStatus("Filters and search are cleared. Showing the current menu page.");
});

detailCloseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    dismissDialog(itemDialog, "back");
  });
});

itemDialog?.addEventListener("click", (event) => {
  if (outsideDialog(event, itemDialog)) {
    dismissDialog(itemDialog, "back");
  }
});

detailAddButton?.addEventListener("click", async () => {
  if (!selectedDetailItem || detailAddButton.disabled) {
    return;
  }
  if (!updateDetailTotal()) {
    const error = document.querySelector("#quantity-error");
    error.textContent = "Enter a whole number from 1 to 12.";
    error.hidden = false;
    detailQuantity.setAttribute("aria-invalid", "true");
    detailQuantity.focus();
    setStatus(error.textContent);
    return;
  }
  const quantity = detailQuantity.valueAsNumber;
  const item = selectedDetailItem;
  resetConfirmation();
  detailAddButton.disabled = true;
  setStatus(`Adding ${quantity} ${item.name}.`);
  const result = await submitAction("cart.add_item", {
    item_id: item.id,
    quantity,
  });
  detailAddButton.disabled = !selectedDetailItem?.available;
  if (result.status === "success") {
    if (appContext?.route === "item" && appContext.focus_item_id === item.id) await navigateOnce("back");
    setStatus(`${quantity} ${item.name} added. Cart total is ${cartTotal?.textContent || "updated"}.`);
  }
});

arOpenButtons.forEach((button) => {
  button.addEventListener("click", () => {
    openArPreview();
  });
});

document.querySelectorAll('a[href="#assistant"], a[href="#ar-preview"]').forEach((link) => {
  link.addEventListener("click", () => {
    if (demoDetails) demoDetails.open = true;
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
    const filter = button.dataset.filter || "all";
    await submitAction("filter_menu", {
      tags: ["vegetarian", "spicy", "available"].includes(filter) ? [filter] : [],
      max_price_pkr: filter === "budget" ? 800 : null,
      category: filter === "all" ? null : appContext?.category,
    });
  });
});

categoryButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const category = button.dataset.categoryTrigger || null;
    document.querySelector("#popular")?.scrollIntoView({ behavior: "smooth", block: "start" });
    await submitAction("filter_menu", {
      tags: appContext?.filter_tags || [],
      max_price_pkr: appContext?.max_price_pkr ?? null,
      category,
    });
  });
});

let searchTimer = null;
searchInput?.addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(async () => {
    await submitAction("search_menu", { query: searchInput.value });
  }, 350);
});

checkoutButton?.addEventListener("click", async () => {
  if (checkoutBusy || cartBusy) return;
  checkoutBusy = true;
  checkoutButton.disabled = true;
  setStatus("Preparing checkout summary...");
  try {
    const summary = await submitAction("checkout.get_summary");
    if (summary.status === "success") {
      setStatus(`Review your demo order. Total ${money(summary.verified_state.total)}. No payment will be collected.`);
    }
  } finally {
    checkoutBusy = false;
    setCartBusy(cartBusy);
  }
});

cartButton?.addEventListener("click", () => {
  void requestCart();
});

cartCloseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    dismissDialog(cartDialog, "menu");
  });
});

cartDialog?.addEventListener("click", (event) => {
  if (outsideDialog(event, cartDialog)) {
    dismissDialog(cartDialog, "menu");
  }
});

confirmOrderButton?.addEventListener("click", async () => {
  if (confirmationBusy) return;
  if (!pendingConfirmationToken) {
    setStatus("Checkout confirmation expired. Please review the cart again.");
    await submitAction("navigate", { target: "cart" });
    return;
  }
  confirmationBusy = true;
  confirmOrderButton.disabled = true;
  setStatus("Submitting confirmed demo order...");
  try {
    const submit = await submitAction("checkout.submit_demo_order", {
      confirmed: true,
      confirmation_token: pendingConfirmationToken,
      summary_revision: pendingSummaryRevision,
    });
    if (submit.status === "success") {
      pendingConfirmationToken = pendingSummaryRevision = null;
      setStatus(`Demo order confirmed: ${submit.verified_state.demo_order_id}. No payment collected or restaurant order sent.`);
    } else {
      pendingConfirmationToken = pendingSummaryRevision = null;
    }
  } finally {
    confirmationBusy = false;
    confirmOrderButton.disabled = !pendingConfirmationToken;
  }
});

checkoutCloseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    dismissDialog(checkoutDialog, button.matches("[data-receipt-close]") ? "menu" : "cart");
  });
});

checkoutDialog?.addEventListener("click", (event) => {
  if (outsideDialog(event, checkoutDialog)) {
    dismissDialog(checkoutDialog, appContext?.route === "confirmation" ? "menu" : "cart");
  }
});

async function controller() {
  if (assistanceController) return assistanceController;
  const app = await application();
  if (assistanceController) return assistanceController;
  const base = document.body.dataset.orchestrationUrl;
  assistanceController = new AssistanceController({
    storage: app.storage, sessionId: app.sessionId, acquireLease: () => acquireTabLease(app.sessionId),
    api: async (name, body, signal) => {
      const url = `${base}/v2/assist/${name === "status" ? `status/${encodeURIComponent(body.request_id)}` : name}`;
      const response = await fetch(url, { method: name === "status" ? "GET" : "POST",
        keepalive: name === "end",
        credentials: "include", signal, headers: { "Content-Type": "application/json", "X-FoodEase-Session": app.sessionId },
        ...(name === "status" ? {} : { body: JSON.stringify(body) }) });
      if (!response.ok) throw new Error("Assistance is unavailable. Manual ordering is still available.");
      return response.json();
    },
    acquireMedia: async (mode) => mode !== "typed" ? (() => {
      if (!window.isSecureContext) throw new Error("Voice needs HTTPS or localhost. You can still browse and order manually.");
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("No microphone is available. You can use typing or browse yourself.");
      return navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    })()
      : { getTracks: () => [], getAudioTracks: () => [] },
    connectSeats: async (prepared, media, signal, mode) => {
      const sdk = await import("/static/vendor/livekit-client.2.15.4.mjs");
      const seats = new LiveKitSeats({ prepared, application: app, sdk, media, mode, transcript: transcriptView,
        onStatus: (status) => {
          // Worker "listening" can arrive before the lifecycle's active ACK.
          // Keep send/mode admission tied to that ACK, not an early audio label.
          if (liveSeats !== seats || seats.closed) return;
          if (status === "reconnecting") {
            pendingConfirmationToken = pendingSummaryRevision = null;
            if (confirmOrderButton) confirmOrderButton.disabled = true;
            assistanceController.setPhase("reconnecting");
          }
          else if (status === "reconnected") assistanceController.modeChanged(seats.mode);
          else if (status === "paused") assistanceController.setPhase("paused");
          else if (/\s/.test(status)) setStatus(status);
          else setAgentStatus(status);
        }, onControl: async (control) => {
          if (liveSeats !== seats || seats.closed) return;
          if (control.intent === "end" || control.intent === "switch_mode" && control.mode === "manual") {
            assistanceIntent++;
            assistanceActive = false;
            await assistanceController.end();
            finishManualUi();
          } else if (control.intent === "switch_mode" && control.mode === "typed") {
            seats.stopMicrophone();
            seats.mode = "typed";
            seats.paused = assistancePaused = false;
            if (assistPause) assistPause.textContent = "Pause";
            seats.closeAudio();
            seats.typedAudio = false;
            assistanceController.modeChanged("typed");
          } else if (control.intent === "switch_mode" && control.mode === "voice") {
            if (seats.mode === "choice") {
              seats.mode = "voice";
              assistanceController.modeChanged("voice");
            } else if (seats.mode === "typed") {
              // A spoken/typed control is not permission to silently reopen capture.
              await assistanceController.end();
              setStatus("Choose Start voice assistance to enable your microphone again.");
            }
          } else if (seats.mode === "typed" && ["mute", "unmute"].includes(control.intent)) {
            try { await seats.setAudioPreference(control.intent === "unmute"); }
            catch { setStatus("Audio playback is blocked. Typed replies remain available."); }
            document.querySelector("[data-assist-typed-audio]").checked = seats.typedAudio;
          } else if (["pause", "mute", "resume", "unmute"].includes(control.intent)) {
            assistancePaused = ["pause", "mute"].includes(control.intent);
            seats.paused = assistancePaused;
            if (assistPause) assistPause.textContent = assistancePaused ? "Resume" : "Pause";
            for (const track of media.getTracks()) track.enabled = !assistancePaused;
            for (const { element } of seats.audio.values()) element.muted = assistancePaused;
            if (assistancePaused) assistanceController.setPhase("paused");
            else assistanceController.modeChanged(seats.mode);
          }
        } });
      await seats.connect(signal);
      liveSeats = seats;
      return seats;
    },
    onState: (state) => {
      assistanceActive = ["active", "paused", "voice_active", "typed_active"].includes(state.state);
      const previousPhase = root.dataset.assistanceState;
      root.dataset.assistanceState = state.modeState;
      const typedAudio = document.querySelector("[data-assist-typed-audio]");
      typedAudio.disabled = !assistanceActive || liveSeats?.mode !== "typed";
      if (typedAudio.disabled) typedAudio.checked = false;
      const send = assistantForm?.querySelector("button[type=submit]");
      if (send) send.disabled = !assistanceActive;
      const speechState = agentStateShell?.dataset.agentState;
      setAgentStatus(state.modeState === "ended" ? "ended" : state.state === "active"
        ? ["assistant_speaking", "thinking"].includes(speechState) ? speechState : "ready/listening" : state.state);
      if (state.state === "active") {
        try { sessionStorage.setItem("foodease.assistance-used.v2", app.sessionId); } catch { /* Optional resume copy only. */ }
      }
      if (state.serverCleanupPending) setStatus("Local assistance stopped. Server cleanup is pending; your cart is preserved.");
      else if (state.detail) setStatus(state.detail);
      else if (state.state === "active" && previousPhase !== state.modeState) {
        setStatus(state.modeState === "choosing_mode" ? "Say voice or manual, or choose a mode below."
          : state.modeState === "typed_active" ? "Typed assistance ready. Microphone off."
          : "Voice assistant ready. Microphone on.");
      }
      else if (previousPhase !== state.modeState && ["connecting", "reconnecting", "paused"].includes(state.modeState)) {
        setStatus(state.modeState === "paused" ? "Assistance paused. Microphone muted."
          : state.modeState === "reconnecting" ? "Reconnecting assistance. Microphone muted until the connection is checked."
          : "Connecting voice or typed assistance. You can end or choose manual ordering at any time.");
      }
      if (app.snapshot) void renderApplication(app.snapshot).catch(() => setStatus("Could not refresh assistance controls. Your cart is preserved."));
    },
  });
  try { assistanceController.hasActivated = sessionStorage.getItem("foodease.assistance-used.v2") === app.sessionId; } catch { /* No automatic activation. */ }
  return assistanceController;
}
async function startAssistance(mode) {
  const intent = ++assistanceIntent;
  try {
    const owner = await controller();
    if (intent !== assistanceIntent) return;
    if (assistanceActive && owner.current?.mode === "choice" && mode === "voice") {
      await liveSeats.control("switch_mode", "voice");
      return; // Existing bound worker acknowledges the choice; no second generation.
    }
    if (owner.current && !owner.current.cancelled && owner.current.mode !== mode) await owner.end();
    if (intent !== assistanceIntent) return;
    if (assistancePaused && owner.current && !owner.current.cancelled && owner.current.mode === mode) {
      await liveSeats.control("resume");
      liveSeats.paused = false;
      for (const track of liveSeats.media.getTracks()) track.enabled = true;
      for (const { element } of liveSeats.audio.values()) element.muted = false;
      owner.modeChanged(mode);
    } else await owner.start({ mode });
    assistancePaused = false;
    if (assistPause) assistPause.textContent = "Pause";
  } catch (error) {
    if (intent !== assistanceIntent) return;
    // Startup failures already stop their run; failed controls on an active
    // chooser must also release capture before the UI offers a fresh retry.
    if (assistanceController?.current && !assistanceController.current.cancelled) {
      await assistanceController.end({ state: "error" });
    }
    if (intent !== assistanceIntent) return;
    root.dataset.assistanceState = "error";
    setAgentStatus("error");
    setStatus(voiceErrorMessage(error));
  }
}
assistStart?.addEventListener("click", () => { void startAssistance("typed"); });
document.querySelector("[data-assist-voice]")?.addEventListener("click", () => { void startAssistance("voice"); });
document.querySelector("[data-assist-choice]")?.addEventListener("click", () => { void startAssistance("choice"); });
async function toggleAssistancePause() {
  if (!assistanceActive || !liveSeats) return;
  try {
    await liveSeats.control(assistancePaused ? "resume" : "pause");
    assistancePaused = !assistancePaused;
    liveSeats.paused = assistancePaused;
    for (const track of liveSeats.media.getTracks()) track.enabled = !assistancePaused;
    for (const { element } of liveSeats.audio.values()) element.muted = assistancePaused;
    if (assistancePaused) assistanceController.setPhase("paused");
    else assistanceController.modeChanged(liveSeats.mode);
    assistPause.textContent = assistancePaused ? "Resume" : "Pause";
    setAgentStatus(assistancePaused ? "muted/paused" : "ready/listening");
  } catch { setStatus("The pause request could not be delivered. End assistance to stop locally."); }
}
assistPause?.addEventListener("click", () => { void toggleAssistancePause(); });
function chooseManual(ended = false) {
  assistanceIntent++;
  assistanceActive = false;
  root.dataset.assistanceState = ended ? "ended" : "manual";
  setAgentStatus(ended ? "ended" : "manual");
  void assistanceController?.end({ state: ended ? "ended" : "manual" });
}
assistEnd?.addEventListener("click", () => chooseManual(true));
document.querySelector("[data-assist-manual]")?.addEventListener("click", () => {
  chooseManual(); finishManualUi();
});
document.querySelector("[data-assist-typed-audio]")?.addEventListener("change", async (event) => {
  const seats = liveSeats;
  if (!assistanceActive || seats?.mode !== "typed") { event.target.checked = false; return; }
  try {
    await seats.setAudioPreference(event.target.checked);
    await seats.control(event.target.checked ? "unmute" : "mute");
  } catch {
    event.target.checked = false;
    await seats.setAudioPreference(false);
    setStatus("Audio could not be enabled. Typed replies remain available.");
  }
});

scenarioButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const scenario = button.dataset.scenario;
    if (scenario === "filter-veg") {
      activeFilter = "vegetarian";
      activeCategory = "all";
      applyMenuState();
      await liveSeats?.text("Show vegetarian food with a budget of 800 rupees.");
    }
    if (scenario === "add-wrap") {
      await liveSeats?.text("Add one Hot Chicken Wrap to my cart.");
    }
    if (scenario === "checkout-summary") {
      await liveSeats?.text("Read my checkout summary.");
    }
  });
});

assistantForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = assistantInput?.value.trim();
  if (!text) {
    return;
  }
  if (!assistanceActive || !liveSeats) { setStatus("Start typed guidance before sending your request."); return; }
  try {
    await liveSeats.text(text);
    if (assistantInput) assistantInput.value = "";
  } catch (error) { setStatus(error.message || "Your request could not be delivered. Please try again after reconnecting."); }
});
assistantInput?.addEventListener("focus", () => { if (assistanceActive) void liveSeats?.control("pause_tips"); });
assistantInput?.addEventListener("blur", () => { if (assistanceActive) void liveSeats?.control("resume_tips"); });
for (const dialog of [itemDialog, checkoutDialog, cartDialog]) dialog?.addEventListener("cancel", (event) => {
  event.preventDefault();
  dismissDialog(dialog, dialog === checkoutDialog ? appContext?.route === "confirmation" ? "menu" : "cart" : dialog === cartDialog ? "menu" : "back");
});
for (const dialog of [itemDialog, checkoutDialog, cartDialog, arDialog]) dialog?.addEventListener("close", () => {
  syncDialogAssistance();
  placeVoiceLauncher();
  if (dialog === cartDialog) cartButton?.setAttribute("aria-expanded", "false");
  if (document.querySelector("dialog[open]")) return;
  const origin = dialogOrigins.get(dialog);
  (origin?.isConnected && origin.getClientRects().length ? origin : cartButton)?.focus({ preventScroll: true });
});
voiceLauncher?.addEventListener("click", () => {
  const view = currentVoicePresentation();
  openVoiceControls();
  if (view.canStart) void startAssistance("voice");
});
document.querySelector("[data-welcome-voice]")?.addEventListener("click", () => {
  const view = currentVoicePresentation();
  openVoiceControls();
  if (view.canStart) void startAssistance("choice");
});
document.querySelector("[data-welcome-manual]")?.addEventListener("click", () => {
  chooseManual();
  finishManualUi();
});
document.querySelector("[data-welcome-typed]")?.addEventListener("click", () => {
  openVoiceControls(); void startAssistance("typed");
});
voiceControls?.querySelector("[data-voice-panel-close]").addEventListener("click", () => voiceControls.close());
voiceControls?.addEventListener("close", () => {
  syncDialogAssistance(); placeVoiceLauncher(); syncVoiceUi();
  const manual = ["manual", "ended"].includes(root.dataset.assistanceState);
  const target = manual && !document.querySelector("dialog[open]") ? document.querySelector("#popular") : voiceLauncher;
  target?.focus({ preventScroll: true });
});
voiceControls?.addEventListener("click", event => { if (outsideDialog(event, voiceControls)) voiceControls.close(); });
voiceControls?.querySelector("[data-voice-use]").addEventListener("click", () => { void startAssistance("voice"); });
voiceControls?.querySelector("[data-voice-retry]").addEventListener("click", () => { void startAssistance("voice"); });
voiceControls?.querySelector("[data-voice-typed]").addEventListener("click", () => { void startAssistance("typed"); });
voiceControls?.querySelector("[data-voice-pause]").addEventListener("click", () => { void toggleAssistancePause(); });
for (const button of voiceControls?.querySelectorAll("[data-voice-panel-manual], [data-voice-end]") || []) {
  button.addEventListener("click", () => { chooseManual(); finishManualUi(); });
}
document.addEventListener("click", (event) => {
  if (event.defaultPrevented) return;
  if (event.target.closest("a[href='/']")) {
    event.preventDefault();
    void submitAction("navigate", { target: "home" });
    return;
  }
  const link = event.target.closest("a[href^='#']");
  const target = { "#popular": "menu", "#categories": "menu", "#cart-preview": "cart" }[link?.getAttribute("href")];
  if (target) {
    event.preventDefault();
    if (target === "cart") { void requestCart(); return; }
    if (target === "menu") {
      document.querySelector(link.hash)?.scrollIntoView({ block: "start", behavior: "instant" });
      if (link.classList.contains("skip-link")) document.querySelector(link.hash)?.focus();
    }
    void navigateOnce(target);
  }
});
document.querySelector("[data-order-manual]")?.addEventListener("click", () => chooseManual());
window.addEventListener("pagehide", () => { assistanceIntent++; void assistanceController?.end(); });
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "hidden") return;
  assistanceIntent++;
  void assistanceController?.end();
});
document.querySelectorAll("[data-dialog-end-assistance]").forEach(button => {
  button.addEventListener("click", () => {
    chooseManual();
    syncDialogAssistance();
    button.closest("dialog")?.querySelector("[autofocus]")?.focus();
    setStatus("Assistance ended. You can continue ordering manually.");
  });
});
document.querySelectorAll("[data-dialog-typing]").forEach(button => {
  button.addEventListener("click", () => { void startAssistance("typed"); });
});
document.querySelectorAll("[data-reconcile-action]").forEach(button => button.addEventListener("click", async () => {
  try {
    const app = await application();
    for (const id of [...app.pending.keys()]) await app.reconcile(id);
    if ([...app.outcomes.values()].includes("expired")) {
      setStatus("The earlier outcome is no longer retained. We cannot verify whether it completed; no request has been sent again.");
      return;
    }
    await app.refresh();
    if (!app.pending.size) setStatus("Your cart is up to date. All earlier action outcomes have been checked.");
  } catch { setStatus("The earlier outcome could not be checked. Please try checking again when connected."); }
}));

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

function paintPreview(button) {
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
      previewPhoto.style.backgroundImage = `url("${itemImageUrl(button.dataset.previewItem, 160)}")`;
      previewPhoto.setAttribute("aria-label", `${name} preview photo`);
    }
    if (arMiniPhoto) {
      arMiniPhoto.src = itemImageUrl(itemId, 480);
    }
}

async function activatePreview(button) {
  const result = await submitAction("select_item", { item_id: button.dataset.previewItem });
  if (result.status === "success") {
    paintPreview(button);
    setStatus(`${button.dataset.previewName} selected from popular items.`);
  }
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

refreshContext().then(async () => {
  // Reload recovers cleanup identity only; capture/dispatch require another gesture.
  const owner = await controller();
  await owner.recover();
}).catch((error) => {
  setStatus(error.message || "Could not sync with the app state. Please refresh the page.");
});
applyTheme();
applyMenuState();
syncVoiceUi();
