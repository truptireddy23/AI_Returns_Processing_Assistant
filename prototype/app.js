// ReturnGuard clickthrough prototype — static, in-memory, no backend.
// AI results are simulated so the interaction design can be demoed.

const IMG = "../validation/transcripts/images/";
const TODAY = "2026-10-01";
const POLICY_VERSION = 2;

const POLICY = {
  P1: "Items may be returned up to and including day 30 after delivery.",
  P3: "Normal wear and tear from use (scuffs, creasing, sole wear, fading) is not a defect and is not eligible for a refund.",
  P2: "Items damaged on arrival or with a manufacturing defect are eligible for a full refund, including shipping, within the return window.",
  P4: "A photo is required for any return claiming damage, a defect, or a wrong item.",
  P5: "Change-of-mind returns must be unused and in original packaging; the customer pays return shipping.",
  P7: "Any refund above $250 requires approval by a returns manager.",
};

const PRODUCTS = [
  { id: "sneakers", name: "Classic White Leather Sneakers", price: 89, category: "Footwear", img: IMG + "IMG-A.jpg" },
  { id: "backpack", name: "Canvas Backpack", price: 64, category: "Bags", emoji: "🎒" },
  { id: "sweater", name: "Wool Sweater", price: 72, category: "Clothing", emoji: "🧶" },
  { id: "shorts", name: "Running Shorts", price: 35, category: "Clothing", emoji: "🩳" },
  { id: "chair", name: "Leather Office Chair", price: 329, category: "Furniture", emoji: "🪑" },
  { id: "speaker", name: "Bluetooth Speaker", price: 79, category: "Electronics", emoji: "🔊" },
];

const REASONS = [
  { id: "damaged", label: "Damaged / defective", needsPhoto: true },
  { id: "wrong", label: "Wrong item received", needsPhoto: true },
  { id: "mind", label: "Changed my mind", needsPhoto: false },
  { id: "fit", label: "Doesn't fit", needsPhoto: false },
];

const PIPELINE = ["Data check", "Policy check", "Photo check", "History check", "AI recommendation", "Governance gate"];

const state = {
  role: "customer",
  cart: [],
  orders: [
    { id: "1042", productId: "sneakers", price: 89, delivered: "2026-09-20" },
    { id: "1037", productId: "shorts", price: 35, delivered: "2026-08-15" },
  ],
  settings: { automation: false, risk: 0.3, confidence: 0.8, highValue: 250 },
  agreement: { agree: 43, total: 50 },
  nextReturn: 220,
  nextOrder: 1050,
  cases: [],
  audit: [],
};

// ---------- seed data ----------

state.cases = [
  {
    id: "R-208", orderId: null, customer: "Jordan Lee", productId: "sneakers", refund: 89,
    delivered: "2026-09-10", reason: "Damaged / defective",
    note: "These look worn out already after a few weeks. Poor quality.",
    photo: IMG + "IMG-C.jpg", status: "needs_review", why: "Low confidence",
    ai: {
      decision: "Escalate", confidence: 62, risk: 0.18,
      whyNot: ["Photo shows scuffing and creases — could be normal wear (P3)", "No clear manufacturing defect is visible"],
      checks: [["ok", "Data complete — photo provided"], ["ok", "Within return window (day 21 of 30)"], ["warn", "Photo: wear vs. defect unclear"], ["ok", "History: low risk (2 returns in 15 orders)"]],
      photoSignal: ["warn", "Shows wear, not a clear defect. Signal only — not a verdict."],
      policy: "P3",
      history: "Account 2 years · 15 orders · 2 returns (both approved) · no linked accounts",
    },
  },
  {
    id: "R-211", orderId: "1037", customer: "Maya Chen", productId: "shorts", refund: 35,
    delivered: "2026-08-15", reason: "Changed my mind", note: "Unused.",
    photo: null, status: "needs_review", why: "Denial",
    ai: {
      decision: "Deny", confidence: 94, risk: 0.08,
      whyNot: ["Confident on the date check; a person must still confirm every denial"],
      checks: [["ok", "Data complete — no photo needed for this reason"], ["bad", "Outside return window (day 47 of 30)"], ["ok", "Photo check not needed"], ["ok", "History: low risk (1 return in 24 orders)"]],
      photoSignal: null,
      policy: "P1",
      history: "Account 3 years · 24 orders · 1 return (approved) · no linked accounts",
    },
  },
  {
    id: "R-214", orderId: null, customer: "Sam Patel", productId: "chair", refund: 329,
    delivered: "2026-09-24", reason: "Changed my mind", note: "Unused and still fully boxed — it doesn't fit my desk.",
    photo: null, status: "needs_review", why: "High value",
    ai: {
      decision: "Approve", confidence: 91, risk: 0.06,
      whyNot: ["Refund is above $250 — a person must approve regardless of confidence (P7)"],
      checks: [["ok", "Data complete — no photo needed for this reason"], ["ok", "Within return window (day 7 of 30)"], ["ok", "Photo check not needed"], ["ok", "History: low risk (1 return in 40 orders)"]],
      photoSignal: null,
      policy: "P7",
      history: "Account 5 years · 40 orders · 1 return (approved) · no linked accounts",
    },
  },
  {
    id: "R-215", orderId: null, customer: "Grace Kim", productId: "sneakers", refund: 89,
    delivered: "2026-09-22", reason: "Damaged / defective", note: "They arrived broken.",
    photo: null, status: "needs_review", why: "Missing photo",
    ai: {
      decision: "None", confidence: null, risk: null,
      whyNot: ["Stopped at the data check: a photo is required for damage claims (P4). The AI did not guess."],
      checks: [["bad", "Data incomplete — no photo for a damage claim"], ["wait", "Policy check skipped"], ["wait", "Photo check skipped"], ["wait", "History check skipped"]],
      photoSignal: null,
      policy: "P4",
      history: "Account 3 years · 21 orders · 0 returns · no linked accounts",
    },
  },
  {
    id: "R-216", orderId: null, customer: "Nina Petrova", productId: "sneakers", refund: 89,
    delivered: "2026-09-19", reason: "Damaged / defective", note: "The upper ripped open on day one.",
    photo: IMG + "IMG-F.jpg", status: "needs_review", why: "Possible fake photo",
    ai: {
      decision: "Escalate", confidence: 55, risk: 0.41,
      whyNot: ["The photo may be AI-generated (lighting and torn edges look synthetic)", "4 returns in 6 months is above average"],
      checks: [["ok", "Data complete — photo provided"], ["ok", "Within return window (day 12 of 30)"], ["bad", "Photo: possible AI-generated image"], ["warn", "History: elevated (4 returns in 9 orders)"]],
      photoSignal: ["error", "Possible AI-generated image. Signal only — a person must judge it."],
      policy: "P2",
      history: "Account 6 months · 9 orders · 4 returns (all approved) · no linked accounts",
    },
  },
  {
    id: "R-205", orderId: null, customer: "Daniel Ortiz", productId: "backpack", refund: 64,
    delivered: "2026-09-22", reason: "Changed my mind", note: "Never used, tags still on.",
    photo: null, status: "approved", why: "Automation off", decidedBy: "Riley (reviewer)",
    ai: {
      decision: "Approve", confidence: 90, risk: 0.05,
      whyNot: ["Automation is off, so a person approved it"],
      checks: [["ok", "Data complete"], ["ok", "Within return window (day 9 of 30)"], ["ok", "Photo check not needed"], ["ok", "History: low risk"]],
      photoSignal: null,
      policy: "P5",
      history: "Account 2 years · 11 orders · 0 returns · no linked accounts",
    },
  },
];

state.audit = [
  ["2026-09-30 16:02", "Reviewer · Riley", "Approved", "R-205", "Agreed with AI (Approve)"],
  ["2026-09-30 15:40", "Gate", "Routed to reviewer", "R-205", "Automation off"],
  ["2026-09-30 15:40", "AI · Recommendation", "Approve (90%)", "R-205", "Policy P5, version 2"],
  ["2026-09-30 15:39", "Customer", "Submitted return", "R-205", "Changed my mind · $64"],
  ["2026-09-29 09:12", "Admin · Priya", "Changed settings", "—", "Automation turned off"],
].map(([time, actor, action, caseId, details]) => ({ time, actor, action, caseId, details }));

// ---------- helpers ----------

const $ = (sel) => document.querySelector(sel);
const product = (id) => PRODUCTS.find((p) => p.id === id);
const findCase = (id) => state.cases.find((c) => c.id === id);
const caseForOrder = (orderId) => state.cases.find((c) => c.orderId === orderId);
const money = (n) => "$" + n.toFixed(2).replace(/\.00$/, "");
const esc = (s) => String(s).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);

function daysSince(dateStr) {
  return Math.round((Date.parse(TODAY) - Date.parse(dateStr)) / 86400000);
}

function fmtDate(dateStr) {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function now() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${TODAY} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function log(actor, action, caseId, details) {
  state.audit.unshift({ time: now(), actor, action, caseId, details });
}

function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function thumb(p) {
  return p.img ? `<img src="${p.img}" alt="${esc(p.name)}">` : p.emoji;
}

function decisionTag(decision) {
  const cls = { Approve: "green", Deny: "red", Escalate: "yellow", None: "gray" }[decision] || "gray";
  return `<span class="tag ${cls}">${decision === "None" ? "— (no decision)" : decision}</span>`;
}

function statusTag(c) {
  const map = {
    checking: ["blue", "Being checked"],
    needs_review: ["purple", "Needs review"],
    approved: ["green", "Approved"],
    auto_approved: ["green", "Auto-approved"],
    denied: ["red", "Denied"],
  };
  const [cls, text] = map[c.status];
  return `<span class="tag ${cls}">${text}</span>`;
}

function band(conf) {
  if (conf == null) return ["—", "var(--border)"];
  if (conf >= 80) return ["High", "var(--green)"];
  if (conf >= 60) return ["Medium", "#b28600"];
  return ["Low", "var(--red)"];
}

// ---------- simulated pipeline ----------

function simulateAI(c) {
  const day = daysSince(c.delivered);
  const needsPhoto = REASONS.find((r) => r.label === c.reason).needsPhoto;
  const checks = [["ok", needsPhoto ? "Data complete — photo provided" : "Data complete — no photo needed for this reason"]];

  if (day > 30) {
    checks.push(["bad", `Outside return window (day ${day} of 30)`], ["ok", "Photo check not needed"], ["ok", "History: low risk"]);
    return { decision: "Deny", confidence: 93, risk: 0.08, policy: "P1", checks, photoSignal: null,
      whyNot: ["Confident on the date check; a person must still confirm every denial"] };
  }
  checks.push(["ok", `Within return window (day ${day} of 30)`]);
  if (needsPhoto) {
    checks.push(["ok", "Photo: matches the product; damage visible (simulated)"], ["ok", "History: low risk"]);
    return { decision: "Approve", confidence: 88, risk: 0.12, policy: "P2", checks,
      photoSignal: ["success", "Matches the product and shows the claimed damage (simulated). Signal only."],
      whyNot: ["Photo checks are signals; confidence is capped below certainty"] };
  }
  checks.push(["ok", "Photo check not needed"], ["ok", "History: low risk"]);
  return { decision: "Approve", confidence: 90, risk: 0.1, policy: "P5", checks, photoSignal: null,
    whyNot: ["Assumes the item is unused, as the customer states"] };
}

function governanceGate(c) {
  const s = state.settings;
  const ai = c.ai;
  if (ai.decision === "Deny") return { auto: false, why: "Denial" };
  if (c.refund > s.highValue) return { auto: false, why: "High value" };
  if (!s.automation) return { auto: false, why: "Automation off" };
  if (ai.risk >= s.risk) return { auto: false, why: "High risk" };
  if (ai.confidence / 100 <= s.confidence) return { auto: false, why: "Low confidence" };
  return { auto: true };
}

function runPipeline(c) {
  c.progress = 0;
  const tick = () => {
    c.progress += 1;
    if (c.progress === PIPELINE.length) {
      c.ai = { ...simulateAI(c), history: "Account 3 years · 24 orders · 1 return (approved) · no linked accounts" };
      log("AI · Recommendation", `${c.ai.decision} (${c.ai.confidence}%)`, c.id, `Policy ${c.ai.policy}, version ${POLICY_VERSION}`);
      const gate = governanceGate(c);
      if (gate.auto) {
        c.status = "auto_approved";
        c.why = "—";
        log("Gate", "Auto-approved", c.id, "All conditions met: automation on, low risk, high confidence, refund within limit");
      } else {
        c.status = "needs_review";
        c.why = gate.why;
        log("Gate", "Routed to reviewer", c.id, gate.why);
      }
    } else {
      const step = PIPELINE[c.progress - 1];
      if (step === "Photo check" && !c.photo) log(`AI · ${step}`, "Skipped", c.id, "No photo needed for this reason");
      else if (step !== "AI recommendation") log(`AI · ${step}`, "Completed", c.id, "—");
      setTimeout(tick, 700);
    }
    if (location.hash === `#/status/${c.id}`) render();
  };
  setTimeout(tick, 700);
}

// ---------- views: customer ----------

function viewShop() {
  return `
    <h1>ShopCo</h1>
    <p class="subtitle">Everyday essentials, delivered.</p>
    <div class="grid products">
      ${PRODUCTS.map((p) => `
        <div class="card product">
          <div class="thumb">${thumb(p)}</div>
          <div class="muted small">${p.category}</div>
          <div class="name">${esc(p.name)}</div>
          <div class="price">${money(p.price)}</div>
          <button class="btn" data-add="${p.id}">Add to cart</button>
        </div>`).join("")}
    </div>`;
}

function viewCart() {
  if (!state.cart.length) {
    return `<h1>Cart</h1><p class="subtitle">Your cart is empty.</p><a class="btn" href="#/shop" style="text-decoration:none;display:inline-block">Browse products</a>`;
  }
  const total = state.cart.reduce((sum, id) => sum + product(id).price, 0);
  return `
    <h1>Cart</h1>
    <p class="subtitle">${state.cart.length} item(s)</p>
    <div class="grid two-col">
      <table>
        <tr><th>Item</th><th>Price</th></tr>
        ${state.cart.map((id) => `<tr><td>${esc(product(id).name)}</td><td>${money(product(id).price)}</td></tr>`).join("")}
        <tr><td><strong>Total</strong></td><td><strong>${money(total)}</strong></td></tr>
      </table>
      <div class="card">
        <h2>Checkout</h2>
        <div class="notice info">Test checkout — no real payment is taken. Use test card 4242 4242 4242 4242.</div>
        <label for="card">Card number</label>
        <input type="text" id="card" placeholder="4242 4242 4242 4242" inputmode="numeric">
        <div id="card-error" class="field-error"></div>
        <div style="margin-top:16px"><button class="btn" id="place-order">Place order · ${money(total)}</button></div>
      </div>
    </div>`;
}

function luhn(num) {
  const digits = num.replace(/\s+/g, "");
  if (!/^\d{13,19}$/.test(digits)) return false;
  let sum = 0;
  [...digits].reverse().forEach((d, i) => {
    let n = Number(d);
    if (i % 2) { n *= 2; if (n > 9) n -= 9; }
    sum += n;
  });
  return sum % 10 === 0;
}

function returnStatusText(c) {
  if (!c) return "";
  const text = { checking: "Return being checked", needs_review: "Return under review", approved: "Return approved",
    auto_approved: "Return approved", denied: "Return not approved" }[c.status];
  return `<a href="#/status/${c.id}">${text} →</a>`;
}

function viewOrders() {
  return `
    <h1>My orders</h1>
    <p class="subtitle">Signed in as Maya Chen</p>
    <table>
      <tr><th>Order</th><th>Item</th><th>Price</th><th>Delivered</th><th></th></tr>
      ${state.orders.map((o) => {
        const p = product(o.productId);
        const c = caseForOrder(o.id);
        return `<tr>
          <td>#${o.id}</td><td>${esc(p.name)}</td><td>${money(o.price)}</td>
          <td>${fmtDate(o.delivered)} <span class="muted small">(day ${daysSince(o.delivered)})</span></td>
          <td>${c ? returnStatusText(c) : `<button class="btn tertiary" data-return="${o.id}">Return item</button>`}</td>
        </tr>`;
      }).join("")}
    </table>`;
}

function viewReturnForm(orderId) {
  const o = state.orders.find((x) => x.id === orderId);
  if (!o) return `<p>Order not found.</p>`;
  const p = product(o.productId);
  return `
    <a href="#/orders" class="small">← My orders</a>
    <h1>Return an item</h1>
    <p class="subtitle">Order #${o.id}</p>
    <div class="card" style="max-width:640px">
      <div class="row">
        <div class="product"><div class="thumb" style="width:80px;height:80px;margin:0;font-size:32px">${thumb(p)}</div></div>
        <div><div><strong>${esc(p.name)}</strong></div><div class="muted">${money(o.price)} · delivered ${fmtDate(o.delivered)}</div></div>
      </div>
      <label for="reason">Reason</label>
      <select id="reason">
        <option value="">Choose a reason</option>
        ${REASONS.map((r) => `<option value="${r.id}">${r.label}</option>`).join("")}
      </select>
      <label for="note">Tell us more</label>
      <textarea id="note" placeholder="What happened?"></textarea>
      <div id="photo-field" hidden>
        <label for="photo">Photo (required for this reason)</label>
        <input type="file" id="photo" accept="image/*">
        <div class="field-hint">A clear photo of the problem helps us decide faster.</div>
        <img id="photo-preview" alt="" style="max-width:160px;margin-top:8px" hidden>
      </div>
      <p class="muted">Refund: ${money(o.price)} to the original payment method.</p>
      <button class="btn" id="submit-return" data-order="${o.id}" disabled>Submit return</button>
    </div>`;
}

function viewStatus(id) {
  const c = findCase(id);
  if (!c) return `<p>Return not found.</p>`;
  const p = product(c.productId);
  const reviewed = c.status === "approved" || c.status === "denied";
  const done = reviewed || c.status === "auto_approved";

  const steps = [
    ["Submitted", "done"],
    ["Being checked", c.status === "checking" ? "current" : "done"],
    [c.status === "auto_approved" ? "Review (not needed)" : "Under review", c.status === "needs_review" ? "current" : (c.status === "checking" ? "" : "done")],
    ["Done", done ? "done" : ""],
  ];

  let body = "";
  if (c.status === "checking") {
    body = `
      <p>We're checking your return now.</p>
      <ul class="checks">
        ${PIPELINE.map((step, i) => {
          const s = i < c.progress ? ["ok", "✓"] : (i === c.progress ? ["wait", "…"] : ["wait", "○"]);
          return `<li><span class="icon ${s[0]}">${s[1]}</span>${step}</li>`;
        }).join("")}
      </ul>`;
  } else if (c.status === "needs_review") {
    body = `<div class="notice info">A member of our team is reviewing your return. We usually respond within 1 business day.</div>`;
  } else if (c.status === "auto_approved") {
    body = `<div class="notice success"><div><strong>Your return is approved.</strong> It met every check in our return policy, so it was approved automatically. ${money(c.refund)} will be refunded to your original payment method.</div></div>`;
  } else if (c.status === "approved") {
    body = `<div class="notice success"><div><strong>Your return is approved.</strong> ${money(c.refund)} will be refunded to your original payment method. Reviewed by a member of our team.</div></div>`;
  } else {
    body = `
      <div class="notice error"><div><strong>Your return was not approved.</strong><br>
        Reason: ${POLICY[c.ai.policy]}<br>
        <strong>This decision was reviewed by a member of our team.</strong></div></div>`;
  }

  return `
    <a href="#/orders" class="small">← My orders</a>
    <h1>Return ${c.id}</h1>
    <p class="subtitle">${esc(p.name)} · ${money(c.refund)} · ${esc(c.reason)}</p>
    <div class="card" style="max-width:720px">
      <div class="progress">
        ${steps.map(([label, cls]) => `<div class="step ${cls}">${label}</div>`).join("")}
      </div>
      ${body}
    </div>`;
}

// ---------- views: reviewer ----------

let queueFilter = "needs_review";

function viewQueue() {
  const rows = state.cases.filter((c) =>
    queueFilter === "all" ? true :
    queueFilter === "needs_review" ? c.status === "needs_review" :
    ["approved", "denied", "auto_approved"].includes(c.status));
  const open = state.cases.filter((c) => c.status === "needs_review").length;
  return `
    <div class="row">
      <div><h1>Review queue</h1><p class="subtitle">${open} case(s) need a person · signed in as Riley</p></div>
      <div class="spacer"></div>
      <div style="width:200px">
        <label for="filter" style="margin-top:0">Show</label>
        <select id="filter">
          <option value="needs_review" ${queueFilter === "needs_review" ? "selected" : ""}>Needs review</option>
          <option value="decided" ${queueFilter === "decided" ? "selected" : ""}>Decided</option>
          <option value="all" ${queueFilter === "all" ? "selected" : ""}>All</option>
        </select>
      </div>
    </div>
    <table>
      <tr><th>Case</th><th>Customer</th><th>Item</th><th>Refund</th><th>AI suggests</th><th>Why here</th><th>Status</th></tr>
      ${rows.length ? rows.map((c) => `
        <tr class="clickable" data-case="${c.id}">
          <td>${c.id}</td><td>${esc(c.customer)}</td><td>${esc(product(c.productId).name)}</td><td>${money(c.refund)}</td>
          <td>${c.ai ? decisionTag(c.ai.decision) : "—"}</td>
          <td><span class="tag gray">${esc(c.why)}</span></td>
          <td>${statusTag(c)}</td>
        </tr>`).join("") : `<tr><td colspan="7" class="muted">Nothing here.</td></tr>`}
    </table>
    <p class="muted small">"Why here" shows why the governance gate sent each case to a person.</p>`;
}

function viewCase(id) {
  const c = findCase(id);
  if (!c || !c.ai) return `<p>Case not found.</p>`;
  const p = product(c.productId);
  const ai = c.ai;
  const [bandText, bandColor] = band(ai.confidence);
  const open = c.status === "needs_review";
  const icon = { ok: "✓", warn: "!", bad: "✕", wait: "○" };

  const decisionLine = ai.decision === "None"
    ? "No recommendation"
    : `${ai.decision} <span class="muted" style="font-size:16px">— ${bandText} confidence (${ai.confidence}%)</span>`;

  return `
    <a href="#/review" class="small">← Review queue</a>
    <div class="row">
      <div><h1>Case ${c.id}</h1>
      <p class="subtitle">${esc(p.name)} · ${money(c.refund)} · ${esc(c.customer)} · delivered ${fmtDate(c.delivered)}</p></div>
      <div class="spacer"></div>${statusTag(c)}
    </div>

    <div class="grid two-col">
      <div class="stack">
        <div class="card rec-box">
          <div class="row"><span class="ai-label">AI</span><h3 style="margin:0">Recommendation</h3></div>
          <div class="rec-decision">${decisionLine}</div>
          <div class="confidence-bar"><div style="width:${ai.confidence || 0}%;background:${bandColor}"></div></div>
          <h3 style="margin-top:16px">${ai.decision === "None" ? "Why there's no recommendation" : "Why not higher"}</h3>
          <ul style="margin:0;padding-left:18px">${ai.whyNot.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>
        </div>
        <div class="card">
          <div class="row"><span class="ai-label">AI</span><h3 style="margin:0">Checks</h3></div>
          <ul class="checks">${ai.checks.map(([s, t]) => `<li><span class="icon ${s}">${icon[s]}</span>${esc(t)}</li>`).join("")}</ul>
        </div>
        <div class="card">
          <h3>Customer's request</h3>
          <dl class="kv">
            <dt>Reason</dt><dd>${esc(c.reason)}</dd>
            <dt>Note</dt><dd>"${esc(c.note)}"</dd>
            <dt>Gate routed here</dt><dd>${esc(c.why)}</dd>
          </dl>
        </div>
      </div>

      <div class="stack">
        <div class="card">
          <h3>Photos</h3>
          <div class="photos">
            <figure>${p.img ? `<img src="${p.img}" alt="Product photo">` : `<div class="placeholder" style="font-size:64px">${p.emoji}</div>`}<figcaption>Product listing</figcaption></figure>
            <figure>${c.photo ? `<img src="${c.photo}" alt="Customer photo">` : `<div class="placeholder">No photo</div>`}<figcaption>Customer's photo</figcaption></figure>
          </div>
          ${ai.photoSignal ? `<div class="notice ${ai.photoSignal[0]}"><span class="ai-label">AI</span><div><strong>Photo check:</strong> ${esc(ai.photoSignal[1])}</div></div>` : ""}
        </div>
        <div class="card">
          <h3>Policy used (version ${POLICY_VERSION})</h3>
          <div class="policy-quote"><strong>${ai.policy}.</strong> ${POLICY[ai.policy]}</div>
        </div>
        <div class="card">
          <h3>Customer history</h3>
          <p style="margin:0">${esc(ai.history)}</p>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      ${open ? `
        <h3>Your decision</h3>
        <div class="decision-bar">
          <button class="btn" id="approve">Approve</button>
          <button class="btn danger" id="deny">Deny…</button>
          <div class="reason">
            <label for="override">Disagree with the AI? Reason (required if you do)</label>
            <input type="text" id="override" placeholder="e.g. Photo clearly shows a split seam, not wear">
            <div id="override-error" class="field-error"></div>
          </div>
        </div>` : `
        <p style="margin:0">Decided: ${statusTag(c)} ${c.decidedBy ? `by ${esc(c.decidedBy)}` : "automatically by the governance gate"}${c.overrideReason ? ` · Override reason: "${esc(c.overrideReason)}"` : ""}</p>`}
    </div>`;
}

function decide(c, decision, reason) {
  const aiPick = c.ai.decision;
  const disagrees = (aiPick === "Approve" || aiPick === "Deny") && aiPick !== decision;
  if (aiPick === "Approve" || aiPick === "Deny") {
    state.agreement.total += 1;
    if (!disagrees) state.agreement.agree += 1;
  }
  c.status = decision === "Approve" ? "approved" : "denied";
  c.decidedBy = "Riley (reviewer)";
  c.overrideReason = disagrees ? reason : "";
  log("Reviewer · Riley", decision === "Approve" ? "Approved" : "Denied (confirmed)", c.id,
    disagrees ? `Overrode AI (${aiPick}): ${reason}` : (aiPick === "Approve" || aiPick === "Deny") ? `Agreed with AI (${aiPick})` : `AI suggested ${aiPick === "None" ? "no decision" : aiPick}${reason ? ` · Note: ${reason}` : ""}`);
  toast(`${c.id} ${decision === "Approve" ? "approved" : "denied"}. Saved to the audit log.`);
  location.hash = "#/review";
}

function needsOverrideReason(c, decision) {
  const aiPick = c.ai.decision;
  return (aiPick === "Approve" || aiPick === "Deny") && aiPick !== decision;
}

function openDenyModal(c, reason) {
  const day = daysSince(c.delivered);
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="deny-title">
      <div class="body">
        <h2 id="deny-title">Deny this return?</h2>
        <dl class="kv">
          <dt>Case</dt><dd>${c.id} · ${esc(product(c.productId).name)} · ${money(c.refund)}</dd>
          <dt>Policy basis</dt><dd><strong>${c.ai.policy}.</strong> ${POLICY[c.ai.policy]}</dd>
          <dt>Delivered</dt><dd>${fmtDate(c.delivered)} (day ${day})</dd>
        </dl>
        <div class="notice warn">The customer will be told this decision was made by a person.</div>
      </div>
      <div class="footer">
        <button class="btn secondary" id="cancel-deny">Cancel</button>
        <button class="btn danger" id="confirm-deny">Confirm denial</button>
      </div>
    </div>`;
  document.body.appendChild(backdrop);
  $("#cancel-deny").onclick = () => backdrop.remove();
  $("#confirm-deny").onclick = () => { backdrop.remove(); decide(c, "Deny", reason); };
  $("#confirm-deny").focus();
}

// ---------- views: admin ----------

function viewAdmin() {
  const s = state.settings;
  const pct = Math.round((state.agreement.agree / state.agreement.total) * 100);
  return `
    <h1>Automation settings</h1>
    <p class="subtitle">Signed in as Priya (admin)</p>
    <div class="grid two-col">
      <div class="card">
        <div class="toggle">
          <label style="margin:0;font-size:14px;color:var(--text)"><strong>Automatic approvals</strong></label>
          <input type="checkbox" id="automation" ${s.automation ? "checked" : ""}>
          <label for="automation" class="track" style="margin:0"></label>
          <span id="automation-text">${s.automation ? "On" : "Off"}</span>
        </div>
        <p class="muted small">Off: every case goes to a person, and the AI only recommends. On: clear, low-risk cases that meet every condition below are approved automatically.</p>
        <label for="risk">Risk must be below</label>
        <input type="number" id="risk" step="0.05" min="0" max="1" value="${s.risk}">
        <label for="conf">Confidence must be above</label>
        <input type="number" id="conf" step="0.05" min="0" max="1" value="${s.confidence}">
        <label for="hv">Refunds above this always need a person ($)</label>
        <input type="number" id="hv" step="10" min="0" value="${s.highValue}">
        <div class="locked">🔒 <div><strong>The AI can never deny a return.</strong><br><span class="muted small">Every denial needs a person. This rule is not configurable.</span></div></div>
        <div style="margin-top:16px"><button class="btn" id="save-settings">Save changes</button></div>
      </div>
      <div class="card">
        <h3>Reviewer–AI agreement</h3>
        <div style="font-size:40px">${pct}%</div>
        <p class="muted">Reviewers agreed with the AI's approve/deny suggestion in ${state.agreement.agree} of the last ${state.agreement.total} decisions.</p>
        <p class="small">Use this as evidence before turning automatic approvals on, and check it after any policy change.</p>
        <a href="#/audit">Open the audit log →</a>
      </div>
    </div>`;
}

let auditFilter = "";

function viewAudit() {
  const rows = state.audit.filter((a) => !auditFilter || a.caseId.toLowerCase().includes(auditFilter.toLowerCase()));
  return `
    <h1>Audit log</h1>
    <p class="subtitle">Every AI step and every human action, newest first.</p>
    <div style="max-width:280px;margin-bottom:16px">
      <label for="audit-filter" style="margin-top:0">Filter by case</label>
      <input type="text" id="audit-filter" placeholder="e.g. R-211" value="${esc(auditFilter)}">
    </div>
    <table>
      <tr><th>Time</th><th>Actor</th><th>Action</th><th>Case</th><th>Details</th></tr>
      ${rows.map((a) => `<tr><td class="small">${a.time}</td><td>${a.actor.startsWith("AI") ? `<span class="ai-label">AI</span> ` : ""}${esc(a.actor.replace(/^AI · /, ""))}</td><td>${esc(a.action)}</td><td>${esc(a.caseId)}</td><td class="small">${esc(a.details)}</td></tr>`).join("")}
    </table>`;
}

// ---------- routing and rendering ----------

const NAV = {
  customer: [["#/shop", "Shop"], ["#/cart", "Cart"], ["#/orders", "My orders"]],
  reviewer: [["#/review", "Review queue"], ["#/audit", "Audit log"]],
  admin: [["#/admin", "Settings"], ["#/review", "Review queue"], ["#/audit", "Audit log"]],
};
const HOME = { customer: "#/shop", reviewer: "#/review", admin: "#/admin" };
const ROLE_OF = { shop: "customer", cart: "customer", orders: "customer", return: "customer", status: "customer", review: "reviewer", case: "reviewer", admin: "admin" };

function renderHeader(route) {
  const nav = NAV[state.role].map(([href, label]) => {
    const text = label === "Cart" && state.cart.length ? `Cart (${state.cart.length})` : label;
    return `<a href="${href}" class="${href === "#/" + route ? "active" : ""}">${text}</a>`;
  }).join("");
  $("#header").innerHTML = `
    <div class="brand">ReturnGuard <span>${state.role === "customer" ? "· ShopCo" : "· Returns desk"}</span></div>
    <nav>${nav}</nav>
    <div class="roles">View as
      ${["customer", "reviewer", "admin"].map((r) => `<button data-role="${r}" class="${state.role === r ? "active" : ""}">${r[0].toUpperCase() + r.slice(1)}</button>`).join("")}
    </div>`;
}

function render() {
  const [route, param] = (location.hash.replace(/^#\//, "") || "shop").split("/");
  if (ROLE_OF[route] && !(route === "review" && state.role === "admin") && !(route === "case" && state.role === "admin")) {
    state.role = ROLE_OF[route];
  }
  renderHeader(route);
  const views = {
    shop: viewShop, cart: viewCart, orders: viewOrders, return: () => viewReturnForm(param),
    status: () => viewStatus(param), review: viewQueue, case: () => viewCase(param),
    admin: viewAdmin, audit: viewAudit,
  };
  $("#app").innerHTML = (views[route] || viewShop)();
  bind(route, param);
}

function bind(route, param) {
  document.querySelectorAll("[data-role]").forEach((b) => (b.onclick = () => {
    state.role = b.dataset.role;
    location.hash = HOME[state.role];
  }));

  document.querySelectorAll("[data-add]").forEach((b) => (b.onclick = () => {
    state.cart.push(b.dataset.add);
    toast(`${product(b.dataset.add).name} added to cart.`);
    renderHeader(route);
  }));

  if (route === "cart" && $("#place-order")) {
    $("#place-order").onclick = () => {
      if (!luhn($("#card").value)) {
        $("#card-error").textContent = "Enter a valid test card number (e.g. 4242 4242 4242 4242).";
        return;
      }
      state.cart.forEach((id) => {
        state.orders.unshift({ id: String(state.nextOrder++), productId: id, price: product(id).price, delivered: TODAY });
      });
      state.cart = [];
      toast("Order placed. For the demo, it's marked as delivered today.");
      location.hash = "#/orders";
    };
  }

  document.querySelectorAll("[data-return]").forEach((b) => (b.onclick = () => (location.hash = `#/return/${b.dataset.return}`)));

  if (route === "return" && $("#submit-return")) {
    let photoUrl = null;
    const update = () => {
      const reason = REASONS.find((r) => r.id === $("#reason").value);
      $("#photo-field").hidden = !(reason && reason.needsPhoto);
      $("#submit-return").disabled = !reason || (reason.needsPhoto && !photoUrl);
    };
    $("#reason").onchange = update;
    $("#photo").onchange = (e) => {
      const file = e.target.files[0];
      photoUrl = file ? URL.createObjectURL(file) : null;
      $("#photo-preview").hidden = !photoUrl;
      if (photoUrl) $("#photo-preview").src = photoUrl;
      update();
    };
    $("#submit-return").onclick = () => {
      const o = state.orders.find((x) => x.id === param);
      const reason = REASONS.find((r) => r.id === $("#reason").value);
      const c = {
        id: `R-${state.nextReturn++}`, orderId: o.id, customer: "Maya Chen", productId: o.productId,
        refund: o.price, delivered: o.delivered, reason: reason.label,
        note: $("#note").value.trim() || "(no note)", photo: reason.needsPhoto ? photoUrl : null,
        status: "checking", why: "—", ai: null,
      };
      state.cases.unshift(c);
      log("Customer", "Submitted return", c.id, `${reason.label} · ${money(c.refund)}`);
      runPipeline(c);
      location.hash = `#/status/${c.id}`;
    };
  }

  if (route === "review" && $("#filter")) {
    $("#filter").onchange = (e) => { queueFilter = e.target.value; render(); };
    document.querySelectorAll("[data-case]").forEach((r) => (r.onclick = () => (location.hash = `#/case/${r.dataset.case}`)));
  }

  if (route === "case" && $("#approve")) {
    const c = findCase(param);
    const attempt = (decision) => {
      const reason = $("#override").value.trim();
      $("#override-error").textContent = "";
      if (needsOverrideReason(c, decision) && !reason) {
        $("#override-error").textContent = `You're disagreeing with the AI (${c.ai.decision}). Add a short reason so it can be reviewed later.`;
        $("#override").focus();
        return;
      }
      if (decision === "Deny") openDenyModal(c, reason);
      else decide(c, "Approve", reason);
    };
    $("#approve").onclick = () => attempt("Approve");
    $("#deny").onclick = () => attempt("Deny");
  }

  if (route === "admin") {
    $("#automation").onchange = (e) => ($("#automation-text").textContent = e.target.checked ? "On" : "Off");
    $("#save-settings").onclick = () => {
      const s = state.settings;
      const next = {
        automation: $("#automation").checked,
        risk: Number($("#risk").value),
        confidence: Number($("#conf").value),
        highValue: Number($("#hv").value),
      };
      const changes = [];
      if (next.automation !== s.automation) changes.push(`Automation turned ${next.automation ? "on" : "off"}`);
      if (next.risk !== s.risk) changes.push(`Risk threshold ${s.risk} → ${next.risk}`);
      if (next.confidence !== s.confidence) changes.push(`Confidence threshold ${s.confidence} → ${next.confidence}`);
      if (next.highValue !== s.highValue) changes.push(`High-value limit $${s.highValue} → $${next.highValue}`);
      if (!changes.length) { toast("No changes to save."); return; }
      state.settings = next;
      log("Admin · Priya", "Changed settings", "—", changes.join("; "));
      toast("Settings saved and recorded in the audit log.");
      render();
    };
  }

  if (route === "audit") {
    $("#audit-filter").oninput = (e) => {
      auditFilter = e.target.value;
      const pos = e.target.selectionStart;
      render();
      $("#audit-filter").focus();
      $("#audit-filter").setSelectionRange(pos, pos);
    };
  }
}

window.addEventListener("hashchange", render);
render();
