// ReturnGuard clickthrough prototype (v1) — static, in-memory, no backend.
// AI results are simulated so the interaction design can be demoed.

const IMG = "../validation/transcripts/images/";
const TODAY = "2026-10-01";
const POLICY_VERSION = 2;

const POLICY = {
  P1: "Items may be returned up to and including day 30 after delivery.",
  P2: "Items damaged on arrival or with a manufacturing defect are eligible for a full refund, including shipping, within the return window.",
  P3: "Normal wear and tear from use (scuffs, creasing, sole wear, fading) is not a defect and is not eligible for a refund.",
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

// Check statuses: ok = clear pass, fail = clear fail, warn = unclear, unverified = cannot be trusted, skip = not run.
const ICON = { ok: "✓", fail: "✕", warn: "!", unverified: "?", skip: "○" };

const PIPELINE = ["Data check (rules)", "Policy check", "Photo match + authenticity", "History check", "AI recommendation", "Governance gate"];

// Escalation is only ever for one of these named reasons.
const REASONS_HERE = ["Proposed denial", "Unverified photo", "Ambiguous call", "High value", "Elevated risk", "Automation off", "Customer review"];

const state = {
  role: "customer",
  cart: [],
  orders: [
    { id: "1042", productId: "sneakers", price: 89, delivered: "2026-09-20" },
    { id: "1037", productId: "shorts", price: 35, delivered: "2026-08-15" },
  ],
  settings: { automation: false, risk: 0.3, highValue: 250 },
  agreement: {
    byCategory: { Footwear: [18, 23], Clothing: [12, 13], Electronics: [9, 10], Bags: [4, 4] },
    overridesByReason: { "Ambiguous call": 9, "Unverified photo": 3, "High value": 1 },
  },
  volume: { returns: 120, escalated: 37 }, // last 7 days, seeded
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
    photo: IMG + "IMG-C.jpg", status: "needs_review", why: "Ambiguous call",
    ai: {
      decision: "Escalate", risk: 0.18, ambiguous: true, photoVerified: true, policy: "P3",
      uncertain: ["Scuffing and creases could be normal wear (P3) rather than a defect (P2)", "The customer says \"poor quality\" after only a few weeks"],
      checks: [["ok", "Data complete — photo provided"], ["ok", "Within return window (day 21 of 30)"], ["ok", "Photo matches the product"], ["ok", "Photo authenticity: no issues found"], ["warn", "Condition: wear vs. defect unclear"], ["ok", "History: low risk (2 returns in 15 orders)"]],
      history: "Account 2 years · 15 orders · 2 returns (both approved) · no linked accounts",
    },
  },
  {
    id: "R-211", orderId: "1037", customer: "Maya Chen", productId: "shorts", refund: 35,
    delivered: "2026-08-15", reason: "Changed my mind", note: "Unused.",
    photo: null, status: "needs_review", why: "Proposed denial",
    ai: {
      decision: "Deny", risk: 0.08, ambiguous: false, photoVerified: null, policy: "P1",
      uncertain: ["Nothing about the date — the window check is computed exactly. A person must still confirm every denial."],
      checks: [["ok", "Data complete — no photo needed for this reason"], ["fail", "Outside return window (day 47 of 30)"], ["ok", "History: low risk (1 return in 24 orders)"]],
      history: "Account 3 years · 24 orders · 1 return (approved) · no linked accounts",
    },
  },
  {
    id: "R-214", orderId: null, customer: "Sam Patel", productId: "chair", refund: 329,
    delivered: "2026-09-24", reason: "Changed my mind", note: "Unused and still fully boxed — it doesn't fit my desk.",
    photo: null, status: "needs_review", why: "High value",
    ai: {
      decision: "Approve", risk: 0.06, ambiguous: false, photoVerified: null, policy: "P7",
      uncertain: ["Nothing in the evidence — but refunds above $250 always need a person (P7)"],
      checks: [["ok", "Data complete — no photo needed for this reason"], ["ok", "Within return window (day 7 of 30)"], ["ok", "History: low risk (1 return in 40 orders)"]],
      history: "Account 5 years · 40 orders · 1 return (approved) · no linked accounts",
    },
  },
  {
    id: "R-215", orderId: null, customer: "Grace Kim", productId: "sneakers", refund: 89,
    delivered: "2026-09-22", reason: "Damaged / defective", note: "They arrived broken.",
    photo: null, status: "needs_info", why: "Missing evidence",
    ai: {
      decision: "None", risk: null, ambiguous: false, photoVerified: null, policy: "P4",
      uncertain: ["Stopped at the rule-based data check: a photo is required for damage claims (P4). No AI step ran; the customer was asked for a photo."],
      checks: [["fail", "Data incomplete — no photo for a damage claim"], ["skip", "Policy check not run"], ["skip", "Photo checks not run"], ["skip", "History check not run"]],
      history: "Account 3 years · 21 orders · 0 returns · no linked accounts",
    },
  },
  {
    id: "R-216", orderId: null, customer: "Nina Petrova", productId: "sneakers", refund: 89,
    delivered: "2026-09-19", reason: "Damaged / defective", note: "The upper ripped open on day one.",
    photo: IMG + "IMG-F.jpg", status: "needs_review", why: "Unverified photo",
    ai: {
      decision: "Escalate", risk: 0.41, ambiguous: false, photoVerified: false, policy: "P2",
      uncertain: ["The photo may be AI-generated (lighting and torn edges look synthetic)", "Heavy wear in the photo contradicts \"ripped on day one\"", "4 returns in 9 orders is above average"],
      checks: [["ok", "Data complete — photo provided"], ["ok", "Within return window (day 12 of 30)"], ["ok", "Photo matches the product"], ["unverified", "Photo authenticity: not verified — possible AI-generated image"], ["warn", "Condition: tear visible, but wear contradicts \"day one\""], ["warn", "History: elevated (4 returns in 9 orders)"]],
      history: "Account 6 months · 9 orders · 4 returns (all approved) · no linked accounts",
    },
  },
  {
    id: "R-205", orderId: null, customer: "Daniel Ortiz", productId: "backpack", refund: 64,
    delivered: "2026-09-22", reason: "Changed my mind", note: "Never used, tags still on.",
    photo: null, status: "approved", why: "Automation off", decidedBy: "Riley (reviewer)",
    ai: {
      decision: "Approve", risk: 0.05, ambiguous: false, photoVerified: null, policy: "P5",
      uncertain: ["Nothing in the evidence — automation was off, so a person approved it"],
      checks: [["ok", "Data complete"], ["ok", "Within return window (day 9 of 30)"], ["ok", "History: low risk"]],
      history: "Account 2 years · 11 orders · 0 returns · no linked accounts",
    },
  },
];

state.audit = [
  ["2026-09-30 16:02", "Reviewer · Riley", "Approved", "R-205", "Agreed with AI (Approve)"],
  ["2026-09-30 15:40", "Gate", "Routed to reviewer", "R-205", "Automation off"],
  ["2026-09-30 15:40", "AI · Recommendation", "Approve · evidence Strong", "R-205", "Policy P5, version 2"],
  ["2026-09-30 15:39", "Customer", "Submitted return", "R-205", "Changed my mind · $64"],
  ["2026-09-30 11:20", "Check · Data (rules)", "Asked customer for a photo", "R-215", "Damage claim without a photo (P4)"],
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
    needs_info: ["gray", "Waiting on customer"],
    needs_review: ["purple", "Needs review"],
    approved: ["green", "Approved"],
    auto_approved: ["green", "Auto-approved"],
    denied: ["red", "Denied"],
  };
  const [cls, text] = map[c.status];
  return `<span class="tag ${cls}">${text}</span>`;
}

// Evidence strength is computed from the checks — never from the model's self-rated confidence.
function strength(ai) {
  const ran = ai.checks.filter(([s]) => s !== "skip");
  const clear = ran.filter(([s]) => s === "ok" || s === "fail").length;
  const warns = ran.filter(([s]) => s === "warn").length;
  const unverified = ran.some(([s]) => s === "unverified");
  let level = "Strong";
  if (unverified || warns >= 2) level = "Weak";
  else if (warns === 1) level = "Mixed";
  return { level, clear, total: ran.length };
}

function strengthTag(ai) {
  if (ai.decision === "None") return `<span class="tag gray">Not assessed</span>`;
  const { level } = strength(ai);
  const cls = { Strong: "green", Mixed: "yellow", Weak: "red" }[level];
  return `<span class="tag ${cls}">Evidence: ${level}</span>`;
}

// ---------- simulated pipeline ----------

function simulateAI(c) {
  const day = daysSince(c.delivered);
  const needsPhoto = REASONS.find((r) => r.label === c.reason).needsPhoto;
  const checks = [["ok", needsPhoto ? "Data complete — photo provided" : "Data complete — no photo needed for this reason"]];
  const history = "Account 3 years · 24 orders · 1 return (approved) · no linked accounts";

  if (day > 30) {
    checks.push(["fail", `Outside return window (day ${day} of 30)`], ["ok", "History: low risk"]);
    return { decision: "Deny", risk: 0.08, ambiguous: false, photoVerified: null, policy: "P1", checks, history,
      uncertain: ["Nothing about the date — the window check is computed exactly. A person must still confirm every denial."] };
  }
  checks.push(["ok", `Within return window (day ${day} of 30)`]);
  if (needsPhoto) {
    checks.push(["ok", "Photo matches the product (simulated)"], ["ok", "Photo authenticity: no issues found (simulated)"],
      ["ok", "Condition: damage consistent with the claim (simulated)"], ["ok", "History: low risk"]);
    return { decision: "Approve", risk: 0.12, ambiguous: false, photoVerified: true, policy: "P2", checks, history,
      uncertain: ["Nothing significant — photo checks are simulated in this prototype"] };
  }
  checks.push(["ok", "History: low risk"]);
  return { decision: "Approve", risk: 0.1, ambiguous: false, photoVerified: null, policy: "P5", checks, history,
    uncertain: ["Assumes the item is unused, as the customer states"] };
}

// The gate decides from check results and fixed rules — not from the model's decision label alone.
function governanceGate(c) {
  const s = state.settings;
  const ai = c.ai;
  if (ai.decision === "Deny") return { auto: false, why: "Proposed denial" };
  if (ai.photoVerified === false) return { auto: false, why: "Unverified photo" };
  if (ai.ambiguous) return { auto: false, why: "Ambiguous call" };
  if (c.refund > s.highValue) return { auto: false, why: "High value" };
  if (ai.risk >= s.risk || strength(ai).level !== "Strong") return { auto: false, why: "Elevated risk" };
  if (!s.automation) return { auto: false, why: "Automation off" };
  return { auto: true };
}

function runPipeline(c) {
  c.progress = 0;
  const tick = () => {
    c.progress += 1;
    if (c.progress === PIPELINE.length) {
      c.ai = simulateAI(c);
      log("AI · Recommendation", `${c.ai.decision} · evidence ${strength(c.ai).level}`, c.id, `Policy ${c.ai.policy}, version ${POLICY_VERSION}`);
      const gate = governanceGate(c);
      state.volume.returns += 1;
      if (gate.auto) {
        c.status = "auto_approved";
        c.why = "—";
        log("Gate", "Auto-approved", c.id, "All checks clear, photo verified or not needed, no ambiguity, low risk, refund within limit");
      } else {
        state.volume.escalated += 1;
        c.status = "needs_review";
        c.why = gate.why;
        log("Gate", "Routed to reviewer", c.id, gate.why);
      }
    } else {
      const step = PIPELINE[c.progress - 1];
      const needsPhoto = REASONS.find((r) => r.label === c.reason).needsPhoto;
      if (step === "Photo match + authenticity" && !needsPhoto) log(`AI · ${step}`, "Skipped", c.id, "No photo needed for this reason");
      else if (step === "Data check (rules)") log("Check · Data (rules)", "Passed", c.id, "All required evidence present");
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
  const text = { checking: "Return being checked", needs_info: "We need more information", needs_review: "Return under review",
    approved: "Return approved", auto_approved: "Return approved", denied: "Return not approved" }[c.status];
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

function evidenceConsidered(c) {
  return c.ai.checks.filter(([s]) => s !== "skip").map(([, t]) => t.replace(/ \(simulated\)$/, "")).join(" · ");
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
          const s = i < c.progress ? ["ok", "✓"] : (i === c.progress ? ["skip", "…"] : ["skip", "○"]);
          return `<li><span class="icon ${s[0]}">${s[1]}</span>${step}</li>`;
        }).join("")}
      </ul>`;
  } else if (c.status === "needs_review") {
    body = c.reviewRequest
      ? `<div class="notice info">You asked for a review. A member of our team will look at your case again and reply within 1 business day.</div>`
      : `<div class="notice info">A member of our team is reviewing your return. We usually respond within 1 business day.</div>`;
  } else if (c.status === "auto_approved") {
    body = `<div class="notice success"><div><strong>Your return is approved.</strong> It met every check in our return policy, so it was approved automatically. ${money(c.refund)} will be refunded to your original payment method.<br><span class="small">Policy rule: ${c.ai.policy} — ${POLICY[c.ai.policy]}</span></div></div>`;
  } else if (c.status === "approved") {
    body = `<div class="notice success"><div><strong>Your return is approved.</strong> ${money(c.refund)} will be refunded to your original payment method. Reviewed by a member of our team.</div></div>`;
  } else if (c.status === "denied") {
    body = `
      <div class="notice error"><div><strong>Your return was not approved.</strong><br>
        Policy rule: <strong>${c.ai.policy}</strong> — ${POLICY[c.ai.policy]}<br>
        We considered: ${esc(evidenceConsidered(c))}<br>
        <strong>This decision was reviewed by a member of our team.</strong></div></div>
      ${c.reviewRequest ? "" : `
        <div id="review-box">
          <p style="margin-bottom:8px"><strong>Think we got it wrong?</strong></p>
          <button class="btn tertiary" id="open-review">Request a review</button>
          <div id="review-form" hidden>
            <label for="review-text">Tell us what we missed</label>
            <textarea id="review-text" placeholder="e.g. The package was held at the depot, so it was delivered later than shown."></textarea>
            <div style="margin-top:12px"><button class="btn" id="send-review" disabled>Send request</button></div>
          </div>
        </div>`}`;
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
    queueFilter === "needs_info" ? c.status === "needs_info" :
    ["approved", "denied", "auto_approved"].includes(c.status));
  const open = state.cases.filter((c) => c.status === "needs_review").length;
  return `
    <div class="row">
      <div><h1>Review queue</h1><p class="subtitle">${open} case(s) need a person · signed in as Riley</p></div>
      <div class="spacer"></div>
      <div style="width:220px">
        <label for="filter" style="margin-top:0">Show</label>
        <select id="filter">
          <option value="needs_review" ${queueFilter === "needs_review" ? "selected" : ""}>Needs review</option>
          <option value="needs_info" ${queueFilter === "needs_info" ? "selected" : ""}>Waiting on customer</option>
          <option value="decided" ${queueFilter === "decided" ? "selected" : ""}>Decided</option>
          <option value="all" ${queueFilter === "all" ? "selected" : ""}>All</option>
        </select>
      </div>
    </div>
    <table>
      <tr><th>Case</th><th>Customer</th><th>Item</th><th>Refund</th><th>AI suggests</th><th>Evidence</th><th>Why here</th><th>Status</th></tr>
      ${rows.length ? rows.map((c) => `
        <tr class="clickable" data-case="${c.id}">
          <td>${c.id}</td><td>${esc(c.customer)}</td><td>${esc(product(c.productId).name)}</td><td>${money(c.refund)}</td>
          <td>${c.ai ? decisionTag(c.ai.decision) : "—"}</td>
          <td>${c.ai ? strengthTag(c.ai) : "—"}</td>
          <td><span class="tag gray">${esc(c.why)}</span></td>
          <td>${statusTag(c)}</td>
        </tr>`).join("") : `<tr><td colspan="8" class="muted">Nothing here.</td></tr>`}
    </table>
    <p class="muted small">"Why here" is always one named reason: ${REASONS_HERE.join(" · ")}. Returns with missing evidence wait on the customer and never reach this queue.</p>`;
}

function viewCase(id) {
  const c = findCase(id);
  if (!c || !c.ai) return `<p>Case not found, or still being checked.</p>`;
  const p = product(c.productId);
  const ai = c.ai;
  const open = c.status === "needs_review";
  const st = strength(ai);

  const banners = [];
  if (ai.photoVerified === false) banners.push(`<div class="notice error"><strong>Unverified photo</strong> — the customer's photo may be AI-generated. A person must judge it; it can never be auto-approved.</div>`);
  if (ai.ambiguous) banners.push(`<div class="notice warn"><strong>Ambiguous call</strong> — wear (P3) vs. defect (P2) depends on judgment, so this case always goes to a person.</div>`);
  if (c.reviewRequest) banners.push(`<div class="notice info"><strong>Customer requested a review:</strong> "${esc(c.reviewRequest)}"</div>`);
  if (c.status === "needs_info") banners.push(`<div class="notice info"><strong>Waiting on the customer</strong> — the rule-based data check asked for a photo before any AI step ran.</div>`);

  return `
    <a href="#/review" class="small">← Review queue</a>
    <div class="row">
      <div><h1>Case ${c.id}</h1>
      <p class="subtitle">${esc(p.name)} · ${money(c.refund)} · ${esc(c.customer)} · delivered ${fmtDate(c.delivered)}</p></div>
      <div class="spacer"></div>${statusTag(c)}
    </div>
    ${banners.join("")}

    <div class="grid two-col" style="margin-top:8px">
      <div class="stack">
        <div class="card rec-box">
          <div class="row"><span class="ai-label">AI</span><h3 style="margin:0">Recommendation</h3></div>
          <div class="rec-decision">${ai.decision === "None" ? "No recommendation" : ai.decision}</div>
          <div class="row" style="margin:6px 0 4px">${strengthTag(ai)}${ai.decision === "None" ? "" : `<span class="muted small">${st.clear} of ${st.total} checks clear</span>`}</div>
          <h3 style="margin-top:16px">Uncertain about</h3>
          <ul style="margin:0;padding-left:18px">${ai.uncertain.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>
        </div>
        <div class="card">
          <h3>Checks</h3>
          <ul class="checks">${ai.checks.map(([s, t]) => `<li><span class="icon ${s}">${ICON[s]}</span>${esc(t)}</li>`).join("")}</ul>
          <p class="muted small" style="margin-bottom:0">Evidence strength is computed from these checks, not from the model's own confidence.</p>
        </div>
        <div class="card">
          <h3>Customer's request</h3>
          <dl class="kv">
            <dt>Reason</dt><dd>${esc(c.reason)}</dd>
            <dt>Note</dt><dd>"${esc(c.note)}"</dd>
            <dt>Why here</dt><dd>${esc(c.why)}</dd>
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
          ${ai.photoVerified === true ? `<div class="notice success"><span class="ai-label">AI</span><div><strong>Authenticity:</strong> no issues found. Signal only — not a verdict.</div></div>` : ""}
          ${ai.photoVerified === false ? `<div class="notice error"><span class="ai-label">AI</span><div><strong>Authenticity: not verified.</strong> Possible AI-generated image. Ask for another photo or inspect the item.</div></div>` : ""}
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
        </div>` : c.status === "needs_info" ? `<p style="margin:0" class="muted">No decision needed until the customer adds the missing photo.</p>` : `
        <p style="margin:0">Decided: ${statusTag(c)} ${c.decidedBy ? `by ${esc(c.decidedBy)}` : "automatically by the governance gate"}${c.overrideReason ? ` · Override reason: "${esc(c.overrideReason)}"` : ""}</p>`}
    </div>`;
}

function decide(c, decision, reason) {
  const aiPick = c.ai.decision;
  const disagrees = (aiPick === "Approve" || aiPick === "Deny") && aiPick !== decision;
  const cat = product(c.productId).category;
  if (aiPick === "Approve" || aiPick === "Deny") {
    const row = state.agreement.byCategory[cat] || (state.agreement.byCategory[cat] = [0, 0]);
    row[1] += 1;
    if (!disagrees) row[0] += 1;
    if (disagrees) state.agreement.overridesByReason[c.why] = (state.agreement.overridesByReason[c.why] || 0) + 1;
  }
  c.status = decision === "Approve" ? "approved" : "denied";
  c.decidedBy = "Riley (reviewer)";
  c.overrideReason = disagrees ? reason : "";
  log("Reviewer · Riley", decision === "Approve" ? "Approved" : "Denied (confirmed)", c.id,
    disagrees ? `Overrode AI (${aiPick}) · ${c.why}: ${reason}` : (aiPick === "Approve" || aiPick === "Deny") ? `Agreed with AI (${aiPick})` : `AI suggested ${aiPick === "None" ? "no decision" : aiPick}${reason ? ` · Note: ${reason}` : ""}`);
  if (decision === "Deny") log("System", "Customer message sent", c.id, "Written after the reviewer confirmed the denial");
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
        <div class="notice warn">The customer will be told this decision was made by a person, and can request a review.</div>
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
  const cats = Object.entries(state.agreement.byCategory);
  const agree = cats.reduce((n, [, [a]]) => n + a, 0);
  const total = cats.reduce((n, [, [, t]]) => n + t, 0);
  const pct = (a, t) => Math.round((a / t) * 100);
  const overrides = Object.entries(state.agreement.overridesByReason).sort((a, b) => b[1] - a[1]);
  const escRate = pct(state.volume.escalated, state.volume.returns);
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
        <p class="muted small">Off: every case goes to a person, and the AI only recommends. On: a case is approved automatically only when every check is clear, any photo is verified, there is no ambiguity, risk is below the limit, and the refund is within the limit.</p>
        <label for="risk">Risk must be below</label>
        <input type="number" id="risk" step="0.05" min="0" max="1" value="${s.risk}">
        <label for="hv">Refunds above this always need a person ($)</label>
        <input type="number" id="hv" step="10" min="0" value="${s.highValue}">
        <div class="locked">🔒 <div><strong>Fixed rules (not configurable)</strong><br>
          <span class="small">The AI can never deny a return. · Unverified photos are never auto-approved. · Ambiguous calls always go to a person.</span></div></div>
        <div style="margin-top:16px"><button class="btn" id="save-settings">Save changes</button></div>
      </div>
      <div class="stack">
        <div class="card">
          <h3>Escalation rate (last 7 days)</h3>
          <div style="font-size:40px">${escRate}%</div>
          <p class="muted small" style="margin:0">${state.volume.escalated} of ${state.volume.returns} returns went to a person. Too high means reviewers are flooded; check which reasons drive it.</p>
        </div>
        <div class="card">
          <h3>Reviewer–AI agreement</h3>
          <div style="font-size:40px">${pct(agree, total)}%</div>
          <p class="muted small">${agree} of the last ${total} approve/deny suggestions.</p>
          <table>
            <tr><th>Product type</th><th>Agreement</th></tr>
            ${cats.map(([cat, [a, t]]) => `<tr><td>${cat}</td><td>${pct(a, t)}% <span class="muted small">(${a}/${t})</span></td></tr>`).join("")}
          </table>
          <p class="small" style="margin-bottom:4px"><strong>Most overrides by reason</strong></p>
          <p class="small muted" style="margin:0">${overrides.map(([r, n]) => `${esc(r)} (${n})`).join(" · ")}</p>
        </div>
        <a href="#/audit">Open the audit log →</a>
      </div>
    </div>`;
}

let auditFilter = "";

function viewAudit() {
  const rows = state.audit.filter((a) => !auditFilter || a.caseId.toLowerCase().includes(auditFilter.toLowerCase()));
  return `
    <h1>Audit log</h1>
    <p class="subtitle">Every check, gate decision, and human action, newest first.</p>
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
  if (ROLE_OF[route] && !((route === "review" || route === "case") && state.role === "admin")) {
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

  if (route === "status" && $("#open-review")) {
    const c = findCase(param);
    $("#open-review").onclick = () => { $("#review-form").hidden = false; $("#open-review").hidden = true; $("#review-text").focus(); };
    $("#review-text").oninput = (e) => ($("#send-review").disabled = !e.target.value.trim());
    $("#send-review").onclick = () => {
      c.reviewRequest = $("#review-text").value.trim();
      c.status = "needs_review";
      c.why = "Customer review";
      log("Customer", "Requested a review", c.id, c.reviewRequest);
      toast("Review requested. A reviewer will look at your case again.");
      render();
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
      const next = { automation: $("#automation").checked, risk: Number($("#risk").value), highValue: Number($("#hv").value) };
      const changes = [];
      if (next.automation !== s.automation) changes.push(`Automation turned ${next.automation ? "on" : "off"}`);
      if (next.risk !== s.risk) changes.push(`Risk limit ${s.risk} → ${next.risk}`);
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
