(() => {
  const root = document.getElementById("pos-app");
  if (!root) return;

  const products = JSON.parse(root.dataset.products || "[]");
  const productMap = new Map(products.map((p) => [Number(p.id), p]));

  const els = {
    search: document.getElementById("pos-product-search"),
    customer: document.getElementById("pos-customer"),
    productTable: document.getElementById("pos-product-table"),
    cartItems: document.getElementById("pos-cart-items"),
    saleId: document.getElementById("pos-sale-id"),
    discountPercent: document.getElementById("pos-discount-percent"),
    discountAmount: document.getElementById("pos-discount-amount"),
    paymentMethod: document.getElementById("pos-payment-method"),
    subtotal: document.getElementById("pos-subtotal"),
    total: document.getElementById("pos-total"),
    applyDiscount: document.getElementById("pos-apply-discount"),
    checkout: document.getElementById("pos-checkout"),
    newSale: document.getElementById("pos-new-sale"),
    receiptLink: document.getElementById("pos-receipt-link"),
    feedback: document.getElementById("pos-feedback"),
  };

  let sale = null;
  let busy = false;

  const money = (n) => Number(n || 0).toFixed(2);

  const setFeedback = (msg, type = "muted") => {
    if (!els.feedback) return;
    els.feedback.className = `small mt-3 text-${type}`;
    els.feedback.textContent = msg || "";
  };

  const setBusy = (state) => {
    busy = state;
    [els.applyDiscount, els.checkout, els.newSale].forEach((b) => {
      if (b) b.disabled = state;
    });
    const buttons = root.querySelectorAll(".pos-add-btn");
    buttons.forEach((b) => {
      b.disabled = state;
    });
  };

  const api = async (url, options = {}) => {
    const res = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.error || `Request failed (${res.status})`;
      throw new Error(msg);
    }
    return data;
  };

  const renderProducts = () => {
    if (!els.productTable) return;
    const term = (els.search?.value || "").trim().toLowerCase();
    const rows = products.filter((p) => {
      if (!term) return true;
      const bag = `${p.name} ${p.category} ${p.barcode || ""}`.toLowerCase();
      return bag.includes(term);
    });

    if (!rows.length) {
      els.productTable.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No products found.</td></tr>`;
      return;
    }

    els.productTable.innerHTML = rows
      .map(
        (p) => `
          <tr>
            <td class="fw-medium">${escapeHtml(p.name)}</td>
            <td>${escapeHtml(p.category)}</td>
            <td class="text-end font-monospace">${money(p.price)}</td>
            <td class="text-end font-monospace">${Number(p.quantity)}</td>
            <td>
              <div class="input-group input-group-sm">
                <input type="number" min="1" step="1" value="1" class="form-control pos-qty-input" data-product-id="${p.id}" />
                <button class="btn btn-pos-outline pos-add-btn" data-product-id="${p.id}" type="button">Add</button>
              </div>
            </td>
          </tr>
        `
      )
      .join("");
  };

  const renderSale = () => {
    els.saleId.textContent = sale?.id ?? "—";
    els.subtotal.textContent = money(sale?.subtotal);
    els.total.textContent = money(sale?.total_amount);
    if (els.receiptLink) {
      if (sale?.status === "completed") {
        els.receiptLink.href = `/receipt/${sale.id}`;
        els.receiptLink.classList.remove("d-none");
      } else {
        els.receiptLink.href = "#";
        els.receiptLink.classList.add("d-none");
      }
    }

    if (!sale || !sale.items || !sale.items.length) {
      els.cartItems.innerHTML = `<div class="text-muted">No items in cart.</div>`;
      return;
    }

    els.cartItems.innerHTML = aggregateSaleLines(sale)
      .map((it) => {
        const p = productMap.get(Number(it.product_id));
        const name = p?.name || `Product #${it.product_id}`;
        return `
          <div class="d-flex justify-content-between align-items-center border-bottom py-1 gap-2">
            <div class="text-truncate">${escapeHtml(name)}</div>
            <div class="d-flex align-items-center gap-1">
              <button class="btn btn-outline-secondary btn-sm py-0 px-2 pos-dec-btn" data-product-id="${it.product_id}" type="button">-</button>
              <span class="font-monospace">${it.quantity}</span>
              <button class="btn btn-outline-secondary btn-sm py-0 px-2 pos-inc-btn" data-product-id="${it.product_id}" type="button">+</button>
            </div>
            <span class="font-monospace">${money(it.line_total)}</span>
          </div>
        `;
      })
      .join("");
  };

  const aggregateSaleLines = (saleValue) => {
    const byProduct = new Map();
    for (const it of saleValue?.items || []) {
      const pid = Number(it.product_id);
      const current = byProduct.get(pid) || { product_id: pid, quantity: 0, line_total: 0 };
      current.quantity += Number(it.quantity || 0);
      current.line_total += Number(it.line_total || 0);
      byProduct.set(pid, current);
    }
    return [...byProduct.values()].sort((a, b) => a.product_id - b.product_id);
  };

  const startNewSale = async () => {
    setBusy(true);
    setFeedback("Starting new sale...", "muted");
    try {
      const customerIdRaw = els.customer?.value || "";
      const payload = customerIdRaw ? { customer_id: Number(customerIdRaw) } : {};
      const data = await api("/sales", { method: "POST", body: JSON.stringify(payload) });
      sale = data.sale;
      renderSale();
      setFeedback("New sale started.", "success");
    } catch (err) {
      setFeedback(err.message, "danger");
    } finally {
      setBusy(false);
    }
  };

  const addItem = async (productId, quantity) => {
    if (!sale?.id) {
      await startNewSale();
      if (!sale?.id) return;
    }
    setBusy(true);
    try {
      const data = await api(`/sales/${sale.id}/items`, {
        method: "POST",
        body: JSON.stringify({ product_id: Number(productId), quantity: Number(quantity) }),
      });
      sale = data.sale;
      renderSale();
      setFeedback("Item added.", "success");
    } catch (err) {
      setFeedback(err.message.includes("Insufficient stock") ? err.message : `Could not add item: ${err.message}`, "danger");
    } finally {
      setBusy(false);
    }
  };

  const rebuildDraftWithQuantities = async (qtyByProduct) => {
    if (!sale?.id) return;
    const oldSale = sale;
    const customerId = oldSale.customer_id;
    const discountPercent = oldSale.discount_percent;
    const discountAmount = oldSale.discount_amount;

    await api(`/sales/${oldSale.id}`, { method: "DELETE" });
    const created = await api("/sales", {
      method: "POST",
      body: JSON.stringify(customerId ? { customer_id: customerId } : {}),
    });
    let nextSale = created.sale;
    for (const [pid, qty] of qtyByProduct.entries()) {
      if (qty <= 0) continue;
      const added = await api(`/sales/${nextSale.id}/items`, {
        method: "POST",
        body: JSON.stringify({ product_id: Number(pid), quantity: Number(qty) }),
      });
      nextSale = added.sale;
    }
    const patched = await api(`/sales/${nextSale.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        discount_percent: Number(discountPercent || 0),
        discount_amount: Number(discountAmount || 0),
      }),
    });
    sale = patched.sale;
  };

  const applyDiscount = async () => {
    if (!sale?.id) {
      setFeedback("Start a sale and add items first.", "warning");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        discount_percent: Number(els.discountPercent.value || 0),
        discount_amount: Number(els.discountAmount.value || 0),
      };
      const data = await api(`/sales/${sale.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      sale = data.sale;
      renderSale();
      setFeedback("Discount applied.", "success");
    } catch (err) {
      setFeedback(err.message, "danger");
    } finally {
      setBusy(false);
    }
  };

  const checkout = async () => {
    if (!sale?.id) {
      setFeedback("Start a sale and add items first.", "warning");
      return;
    }
    setBusy(true);
    try {
      const method = els.paymentMethod.value || "cash";
      const data = await api(`/sales/${sale.id}/complete`, {
        method: "POST",
        body: JSON.stringify({ payment_method: method }),
      });
      sale = data.sale;
      const receiptUrl = `/receipt/${sale.id}`;
      renderSale();
      if (els.receiptLink) {
        els.receiptLink.href = receiptUrl;
        els.receiptLink.classList.remove("d-none");
      }
      setFeedback(`Sale completed. Receipt #${sale.id} ready.`, "success");
      // Non-blocking: open printable receipt in a new tab right after checkout.
      window.open(receiptUrl, "_blank", "noopener");
    } catch (err) {
      setFeedback(err.message, "danger");
    } finally {
      setBusy(false);
    }
  };

  const escapeHtml = (value) =>
    String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  root.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".pos-add-btn");
    if (!btn || busy) return;
    const productId = Number(btn.dataset.productId);
    const qtyInput = root.querySelector(`.pos-qty-input[data-product-id="${productId}"]`);
    const qty = Number(qtyInput?.value || 1);
    if (!Number.isFinite(qty) || qty <= 0) {
      setFeedback("Quantity must be a positive number.", "warning");
      return;
    }
    addItem(productId, qty);
  });

  root.addEventListener("click", async (ev) => {
    const inc = ev.target.closest(".pos-inc-btn");
    if (inc && !busy) {
      const productId = Number(inc.dataset.productId);
      addItem(productId, 1);
      return;
    }

    const dec = ev.target.closest(".pos-dec-btn");
    if (!dec || busy || !sale?.id) return;
    const productId = Number(dec.dataset.productId);
    const lines = aggregateSaleLines(sale);
    const current = lines.find((x) => Number(x.product_id) === productId);
    if (!current) return;

    const nextQty = Number(current.quantity) - 1;
    const nextMap = new Map(lines.map((x) => [Number(x.product_id), Number(x.quantity)]));
    if (nextQty <= 0) nextMap.delete(productId);
    else nextMap.set(productId, nextQty);

    setBusy(true);
    try {
      await rebuildDraftWithQuantities(nextMap);
      renderSale();
      setFeedback("Cart quantity updated.", "success");
    } catch (err) {
      setFeedback(`Could not reduce quantity: ${err.message}`, "danger");
    } finally {
      setBusy(false);
    }
  });

  els.search?.addEventListener("input", renderProducts);
  els.customer?.addEventListener("change", () => {
    if (!sale?.id) return;
    setFeedback("Customer changes apply when you start a new sale.", "warning");
  });
  els.applyDiscount?.addEventListener("click", applyDiscount);
  els.checkout?.addEventListener("click", checkout);
  els.newSale?.addEventListener("click", startNewSale);

  renderProducts();
  renderSale();
})();
