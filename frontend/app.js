/**
 * AgentPay — Frontend Observability Controller
 * Modern light SaaS dashboard syncing with backend audit events in real time.
 */

(() => {
  // State
  const state = {
    sessionId: null,
    knownEventIds: new Set(),
    selectedOrderId: 'auto',
    activeOrder: null,
    recentEvents: [],
    timelineEvents: [],
    isFirstPoll: true,
    isSyncing: false,
};

  // DOM Elements
  const elements = {
    activityFeed: document.getElementById('activityFeed'),
    eventCountBadge: document.getElementById('eventCountBadge'),
    orderCard: document.getElementById('orderCard'),
    orderSelect: document.getElementById('orderSelect'),
    timelineContainer: document.getElementById('timelineContainer'),
    timelineOrderBadge: document.getElementById('timelineOrderBadge'),
    timelineMeta: document.getElementById('timelineMeta'),
    syncText: document.getElementById('syncText'),
    syncStatus: document.getElementById('syncStatus'),
    refreshBtn: document.getElementById('refreshBtn'),
    authorizationAgentId: document.getElementById('authorizationAgentId'),
    authorizationToken: document.getElementById('authorizationToken'),
    authorizationStatus: document.getElementById('authorizationStatus'),
    generateAuthorizationBtn: document.getElementById('generateAuthorizationBtn'),
    policyMaximum: document.getElementById('policyMaximum'),
    policyApproval: document.getElementById('policyApproval'),
    policyVerification: document.getElementById('policyVerification'),
    policyMessage: document.getElementById('policyMessage'),
    savePolicyBtn: document.getElementById('savePolicyBtn'),
  };

  const API_BASE = window.location.origin;

  // Formatters
  function formatTime(isoString) {
    if (!isoString) return '--:--:--';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  }

  function formatCurrency(amount, currency = 'INR') {
    if (amount === undefined || amount === null) return '₹0.00';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency || 'INR',
    }).format(amount);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // =========================================================================
  // API Fetchers
  // =========================================================================


  async function fetchActiveSession() {
    const res = await fetch(`${API_BASE}/session/active`);

    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }

    return await res.json();
  }

  async function fetchRecentAudit() {
    if (!state.sessionId) return [];

    const res = await fetch(
        `${API_BASE}/audit/recent?limit=50&session_id=${encodeURIComponent(state.sessionId)}`
    );

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    return await res.json();
  }

  async function fetchLatestOrder() {
    const query = state.sessionId
      ? `?session_id=${encodeURIComponent(state.sessionId)}`
      : '';
    const res = await fetch(`${API_BASE}/orders/latest${query}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async function fetchOrdersList() {
    if (!state.sessionId) return [];
    const res = await fetch(
      `${API_BASE}/orders?limit=25&session_id=${encodeURIComponent(state.sessionId)}`
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async function fetchOrderHistory(orderId) {
    if (!orderId) return [];
    const res = await fetch(`${API_BASE}/orders/${encodeURIComponent(orderId)}/history`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async function fetchActiveAuthorization() {
    const res = await fetch(`${API_BASE}/authorization/active`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async function fetchActivePolicy() {
    const res = await fetch(`${API_BASE}/policy/active`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  function renderPolicy(policy) {
    if (!policy) return;
    elements.policyMaximum.value = policy.maximum_transaction_amount;
    elements.policyApproval.value = policy.approval_threshold;
    elements.policyVerification.checked = policy.payment_verification_required;
  }

  async function savePolicy() {
    elements.savePolicyBtn.disabled = true;
    elements.policyMessage.textContent = '';
    try {
      const res = await fetch(`${API_BASE}/policy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          maximum_transaction_amount: Number(elements.policyMaximum.value),
          approval_threshold: Number(elements.policyApproval.value),
          payment_verification_required: elements.policyVerification.checked,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      renderPolicy(data);
      elements.policyMessage.textContent = 'Policy saved';
    } catch (error) {
      elements.policyMessage.textContent = 'Unable to save policy';
      console.error('Policy update failed:', error);
    } finally {
      elements.savePolicyBtn.disabled = false;
    }
  }

  function renderAuthorization(authorization) {
    if (!authorization) return;
    elements.authorizationAgentId.textContent = authorization.agent_id;
    elements.authorizationStatus.textContent = 'Authorized';
    elements.authorizationStatus.classList.add('authorization-status-authorized');
  }

  async function generateAuthorization() {
    elements.generateAuthorizationBtn.disabled = true;
    try {
      const res = await fetch(`${API_BASE}/authorization/generate`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

      elements.authorizationAgentId.textContent = data.agent_id;
      elements.authorizationToken.textContent = data.authorization_token;
      elements.authorizationStatus.textContent = 'Authorized';
      elements.authorizationStatus.classList.add('authorization-status-authorized');
      elements.generateAuthorizationBtn.textContent = 'Authorized';
      fetchActivePolicy()
        .then(renderPolicy)
        .catch(error => console.error('Policy lookup failed:', error));
    } catch (error) {
      console.error('Authorization generation failed:', error);
      elements.generateAuthorizationBtn.disabled = false;
    }
  }

  // =========================================================================
  // Renderers
  // =========================================================================

  function renderActivityFeed(events) {
    if (!events || events.length === 0) {
      if (state.knownEventIds.size === 0) {
        elements.activityFeed.innerHTML = `
          <div class="feed-empty-state">
            <div class="spinner-ring"></div>
            <p class="empty-lead">Waiting for Claude to execute commerce tools</p>
            <p class="empty-sub">Prompt Claude: <em>"Find black running shoes under ₹5000"</em></p>
          </div>
        `;
      }
      return;
    }

    const emptyState = elements.activityFeed.querySelector('.feed-empty-state');
    if (emptyState) {
      elements.activityFeed.innerHTML = '';
    }

    events.forEach((evt) => {
      const isNew = !state.knownEventIds.has(evt.id);
      if (isNew) {
        state.knownEventIds.add(evt.id);
        const card = createActivityItem(evt, !state.isFirstPoll);
        elements.activityFeed.prepend(card);
      }
    });

    elements.eventCountBadge.textContent = `${state.knownEventIds.size} events`;
  }

  function createActivityItem(evt, highlight = false) {
    const item = document.createElement('div');
    const eventState = getEventState(evt);
    item.className = `activity-item activity-${eventState} ${highlight ? 'item-fresh' : ''}`;
    item.dataset.eventId = evt.id;

    const toolName = evt.tool_name || 'event';
    const timeStr = formatTime(evt.timestamp);
    const decision = evt.decision || evt.result?.status || 'recorded';
    const reason = evt.reason || 'Event recorded';

    let headline = '';
    let metaHtml = '';

    if (toolName === 'catalog_search') {
      const query = evt.input?.query || 'All products';
      const returnedProducts = Array.isArray(evt.result?.products)
        ? evt.result.products
        : [];
      const count = returnedProducts.length || evt.result?.count ||
        evt.result?.product_ids?.length || 0;
      headline = `Searching catalog for "${escapeHtml(query)}"`;
      metaHtml = `
        <div class="meta-field">
          <span class="meta-label">Status:</span>
          <span class="meta-val" style="color: var(--success)">✓ Completed</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Found:</span>
          <span class="meta-val">${count} items</span>
        </div>
      `;
    } else if (toolName === 'order_created') {
      const orderId = evt.order_id || evt.result?.order_id || '—';
      const amount = evt.result?.amount;
      const qty = evt.result?.qty || 1;
      headline = `Order initiated &bull; ${escapeHtml(orderId)}`;
      metaHtml = `
        <div class="meta-field">
          <span class="meta-label">Order:</span>
          <span class="meta-val meta-link" onclick="window.selectOrder('${escapeHtml(orderId)}')">${escapeHtml(orderId)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Quantity:</span>
          <span class="meta-val">${qty}</span>
        </div>
        ${amount ? `
        <div class="meta-field">
          <span class="meta-label">Amount:</span>
          <span class="meta-val">${formatCurrency(amount)}</span>
        </div>` : ''}
      `;
    } else if (toolName === 'payment_initiated') {
      const orderId = evt.order_id || '—';
      const linkId = evt.result?.payment_link_id || '—';
      const amount = evt.result?.amount;
      headline = `Payment initiated &bull; Link generated`;
      metaHtml = `
        <div class="meta-field">
          <span class="meta-label">Order:</span>
          <span class="meta-val meta-link" onclick="window.selectOrder('${escapeHtml(orderId)}')">${escapeHtml(orderId)}</span>
        </div>
        ${amount ? `
        <div class="meta-field">
          <span class="meta-label">Amount:</span>
          <span class="meta-val">${formatCurrency(amount)}</span>
        </div>` : ''}
        <div class="meta-field">
          <span class="meta-label">Link ID:</span>
          <span class="meta-val">${escapeHtml(linkId)}</span>
        </div>
      `;
    } else if (toolName === 'payment_status_changed') {
      const orderId = evt.order_id || '—';
      const status = evt.result?.status || evt.decision || '—';
      headline = `Payment status updated: ${escapeHtml(status)}`;
      metaHtml = `
        <div class="meta-field">
          <span class="meta-label">Order:</span>
          <span class="meta-val meta-link" onclick="window.selectOrder('${escapeHtml(orderId)}')">${escapeHtml(orderId)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Gateway Status:</span>
          <span class="meta-val">${escapeHtml(evt.result?.razorpay_status || status)}</span>
        </div>
      `;
    } else if (toolName === 'payment_finished') {
      const orderId = evt.order_id || '—';
      const paymentId = evt.result?.payment_id || '—';
      const amountPaid = evt.result?.amount_paid;
      headline = `Payment successfully completed &bull; ${amountPaid ? formatCurrency(amountPaid) : ''} paid`;
      metaHtml = `
        <div class="meta-field">
          <span class="meta-label">Order:</span>
          <span class="meta-val meta-link" onclick="window.selectOrder('${escapeHtml(orderId)}')">${escapeHtml(orderId)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Payment ID:</span>
          <span class="meta-val">${escapeHtml(paymentId)}</span>
        </div>
      `;
    } else if (toolName === 'order_placed') {
      const orderId = evt.order_id || '—';
      headline = `Order placed &amp; confirmed for delivery`;
      metaHtml = `
        <div class="meta-field">
          <span class="meta-label">Order:</span>
          <span class="meta-val meta-link" onclick="window.selectOrder('${escapeHtml(orderId)}')">${escapeHtml(orderId)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">State:</span>
          <span class="meta-val" style="color: var(--success)">✓ Completed</span>
        </div>
      `;
    } else {
      headline = escapeHtml(evt.reason || toolName);
      metaHtml = `
        <div class="meta-field">
          <span class="meta-label">Result:</span>
          <span class="meta-val">${escapeHtml(evt.decision || 'ok')}</span>
        </div>
      `;
    }

    item.innerHTML = `
      <div class="activity-top-row">
        <span class="event-pill pill-${escapeHtml(toolName)}">
          ${escapeHtml(toolName)}
        </span>
        <span class="event-state state-${eventState}">${escapeHtml(decision)}</span>
        <span class="activity-time">${timeStr}</span>
      </div>
      <div class="activity-headline">${headline}</div>
      <div class="activity-reason" title="${escapeHtml(reason)}">${escapeHtml(reason)}</div>
      <div class="activity-meta-tags">
        ${metaHtml}
      </div>
    `;

    return item;
  }

  function getEventState(evt) {
    if (['catalog_search', 'order_created', 'payment_finished', 'order_placed'].includes(evt.tool_name)) {
      return 'success';
    }
    if (evt.tool_name === 'payment_initiated') {
      return 'pending';
    }
    const status = String(evt.result?.status || evt.decision || '').toLowerCase();
    if (['failed', 'failure', 'error', 'cancelled', 'rejected'].some(value => status.includes(value))) {
      return 'warning';
    }
    if (['pending', 'created', 'initiated', 'partially_paid'].some(value => status.includes(value))) {
      return 'pending';
    }
    return 'success';
  }

  function renderCurrentOrder(order, history = []) {
    if (!order) {
      elements.orderCard.innerHTML = `
        <div class="order-card-placeholder">
          <p>No active order selected</p>
          <span>Ask Claude to purchase a product to start an order.</span>
        </div>
      `;
      return;
    }

    const historyTools = new Set(history.map(h => h.tool_name));
    const isOrderCreated = true;
    const isPaymentInitiated = historyTools.has('payment_initiated') || !!order.razorpay_payment_link_id;
    const isPaid = historyTools.has('payment_finished') || order.status === 'paid';
    const isPlaced = historyTools.has('order_placed') || order.status === 'paid';
    const orderState = ['failed', 'cancelled', 'rejected', 'error'].some(
      value => String(order.status).toLowerCase().includes(value)
    ) ? 'warning' : ['paid', 'approved'].includes(order.status) ? 'success' : 'pending';
    const orderStatusLabel = orderState === 'warning'
      ? 'Failed'
      : orderState === 'success'
        ? (isPlaced ? 'Completed' : order.status === 'approved' ? 'Approved' : 'Paid')
        : 'Pending Payment';
    const approvalPanel = order.status === 'approval_required' ? `
      <div class="approval-panel">
        <div class="approval-title">User Approval Required</div>
        <p>This transaction exceeds your automatic approval threshold.</p>
        <div class="approval-summary">
          <span>Amount: <strong>${formatCurrency(order.amount, order.currency)}</strong></span>
          <span>Threshold: <strong>${formatCurrency(Number(elements.policyApproval.value), order.currency)}</strong></span>
        </div>
        <button class="btn-pay-link approval-button" type="button" onclick="window.approveOrder('${escapeHtml(order.order_id)}')">
          Approve Transaction
        </button>
      </div>
    ` : order.status === 'approved' ? `
      <div class="approval-confirmation">✓ Transaction Approved</div>
    ` : '';

    elements.orderCard.innerHTML = `
      <!-- Order Overview Box -->
      <div class="order-overview-box">
        <div class="order-title-row">
          <div class="order-number">Order #${escapeHtml(order.order_id)}</div>
          <span class="order-status-badge order-state-${orderState}">
            ${orderState === 'success' ? '✓ ' : orderState === 'warning' ? '! ' : '● '}${orderStatusLabel}
          </span>
        </div>

        <div class="order-product-line">
          <span>${escapeHtml(order.product_name || order.item_id)}</span>
          <span class="product-qty-pill">Qty ${order.qty}</span>
        </div>

        <div class="order-price-row">
          <span class="price-label">Total Amount</span>
          <span class="price-value">${formatCurrency(order.amount, order.currency)} <span style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted);">${escapeHtml(order.currency)}</span></span>
        </div>
      </div>

      ${approvalPanel}

      <!-- Clean Horizontal Progress Stepper -->
      <div class="progress-stepper-card">
        <div class="stepper-header-title">Order Status Progression</div>
        <div class="stepper-horizontal">
          <div class="stepper-point ${isOrderCreated ? 'done' : 'active'}">
            <div class="step-circle">${isOrderCreated ? '✓' : '1'}</div>
            <span class="step-caption">Created</span>
          </div>

          <div class="stepper-line ${isPaymentInitiated ? 'line-done' : ''}"></div>

          <div class="stepper-point ${isPaymentInitiated ? (isPaid ? 'done' : 'active') : ''}">
            <div class="step-circle">${isPaid ? '✓' : (isPaymentInitiated ? '●' : '2')}</div>
            <span class="step-caption">Payment</span>
          </div>

          <div class="stepper-line ${isPaid ? 'line-done' : ''}"></div>

          <div class="stepper-point ${isPaid ? 'done' : ''}">
            <div class="step-circle">${isPaid ? '✓' : '3'}</div>
            <span class="step-caption">Paid</span>
          </div>

          <div class="stepper-line ${isPlaced ? 'line-done' : ''}"></div>

          <div class="stepper-point ${isPlaced ? 'done' : ''}">
            <div class="step-circle">${isPlaced ? '✓' : '4'}</div>
            <span class="step-caption">Placed</span>
          </div>
        </div>
      </div>

      <!-- Payment Details Section -->
      <div class="payment-info-card">
        <div class="payment-info-title">Payment Details</div>

        <div class="info-row">
          <span class="info-key">Razorpay Order ID</span>
          <span class="info-val">${escapeHtml(order.razorpay_order_id || 'Not generated')}</span>
        </div>

        <div class="info-row">
          <span class="info-key">Payment Link ID</span>
          <span class="info-val">${escapeHtml(order.razorpay_payment_link_id || 'None')}</span>
        </div>

        <div class="info-row">
          <span class="info-key">Payment ID</span>
          <span class="info-val">${escapeHtml(order.razorpay_payment_id || 'Awaiting Payment')}</span>
        </div>

        ${order.razorpay_payment_link_id ? `
        <a href="https://rzp.io/i/${encodeURIComponent(order.razorpay_payment_link_id)}"
           target="_blank"
           rel="noopener noreferrer"
           class="btn-pay-link">
           Open Payment Link &rarr;
        </a>` : ''}
      </div>
    `;
  }

  function renderTimeline(history, orderId) {
    elements.timelineOrderBadge.textContent = orderId ? `#${orderId}` : 'ORD-—';

    if (!history || history.length === 0) {
      elements.timelineContainer.innerHTML = `
        <div class="timeline-empty">
          <p>No audit trail recorded yet for ${escapeHtml(orderId || 'this order')}.</p>
        </div>
      `;
      elements.timelineMeta.textContent = '0 lifecycle events';
      return;
    }

    elements.timelineMeta.textContent = `${history.length} lifecycle events recorded`;

    let cardsHtml = '';

    history.forEach((log, index) => {
      const toolName = log.tool_name || 'event';
      const timeStr = formatTime(log.timestamp);
      const isLast = index === history.length - 1;

      // Friendly display labels
      const titles = {
        order_created: 'Order Created',
        payment_initiated: 'Payment Initiated',
        payment_status_changed: 'Payment Status Sync',
        payment_finished: 'Payment Finished',
        order_placed: 'Order Placed',
      };
      const displayTitle = titles[toolName] || toolName;

      let snippet = '';
      if (toolName === 'order_created') {
        snippet = `Amount: ${formatCurrency(log.result?.amount)}, Qty: ${log.result?.qty || 1}`;
      } else if (toolName === 'payment_initiated') {
        snippet = `Link: ${log.result?.payment_link_id || '—'}`;
      } else if (toolName === 'payment_status_changed') {
        snippet = `Status: ${log.result?.status || log.decision}`;
      } else if (toolName === 'payment_finished') {
        snippet = `Payment ID: ${log.result?.payment_id || '—'}`;
      } else if (toolName === 'order_placed') {
        snippet = `Order successfully completed`;
      }

      cardsHtml += `
        <div class="timeline-card-node">
          <div class="node-header-line">
            <div class="node-title-group">
              <span class="node-check">✓</span>
              <span class="node-name">${escapeHtml(displayTitle)}</span>
            </div>
            <span class="node-timestamp">${timeStr}</span>
          </div>
          <div class="node-desc">${escapeHtml(log.reason || '')}</div>
          ${snippet ? `<div class="node-snippet">${escapeHtml(snippet)}</div>` : ''}
        </div>
      `;

      if (!isLast) {
        cardsHtml += `<div class="timeline-arrow">&rarr;</div>`;
      }
    });

    elements.timelineContainer.innerHTML = `
      <div class="timeline-row">
        ${cardsHtml}
      </div>
    `;
  }

  // =========================================================================
  // Polling Loop
  // =========================================================================

  async function pollCycle() {
    if (state.isSyncing) return;

    state.isSyncing = true;

    try {
        // ============================================================
        // 0. Check which Claude/MCP session is currently active
        // ============================================================

        const activeSession = await fetchActiveSession();
        const newSessionId = activeSession?.session_id || null;

        // ============================================================
        // 1. Detect a NEW Claude/MCP session
        // ============================================================

        if (newSessionId && newSessionId !== state.sessionId) {
            console.log(
                `New MCP session detected: ${newSessionId}`
            );

            // Store the new session
            state.sessionId = newSessionId;

            // Clear all previous session state
            state.knownEventIds.clear();
            state.recentEvents = [];
            state.timelineEvents = [];
            state.activeOrder = null;

            // Return order selection to automatic mode
            state.selectedOrderId = 'auto';

            // Clear old order dropdown options
            elements.orderSelect.innerHTML = `
                <option value="auto">Auto-track Latest</option>
            `;

            // Clear old activity immediately
            elements.activityFeed.innerHTML = `
                <div class="feed-empty-state">
                    <div class="spinner-ring"></div>
                    <p class="empty-lead">
                        Waiting for Claude to execute commerce tools
                    </p>
                    <p class="empty-sub">
                        New commerce session started
                    </p>
                </div>
            `;

            // Clear old order
            renderCurrentOrder(null);

            // Clear old timeline
            renderTimeline([], null);

            // Reset event counter
            elements.eventCountBadge.textContent = '0 events';
        }

        // ============================================================
        // 2. Fetch ONLY audit events for current Claude session
        // ============================================================

        const recentAudit = await fetchRecentAudit();

        state.recentEvents = recentAudit;

        renderActivityFeed(recentAudit);

        // ============================================================
        // 3. Fetch orders
        // ============================================================

        const orders = await fetchOrdersList();

        // IMPORTANT:
        // Only keep orders belonging to the current session.
        const sessionOrders = state.sessionId
            ? orders.filter(
                order => order.session_id === state.sessionId
              )
            : [];

        updateOrderDropdown(sessionOrders);

        // ============================================================
        // 4. Determine active order
        // ============================================================

        let currentOrder = null;

        if (state.selectedOrderId === 'auto') {

            // Find newest order belonging to this session
            currentOrder = sessionOrders.length > 0
                ? sessionOrders[0]
                : null;

        } else {

            currentOrder = sessionOrders.find(
                order => order.order_id === state.selectedOrderId
            ) || null;
        }

        state.activeOrder = currentOrder;

        // ============================================================
        // 5. Fetch chronological history for active order
        // ============================================================

        if (currentOrder && currentOrder.order_id) {

            const history = await fetchOrderHistory(
                currentOrder.order_id
            );

            state.timelineEvents = history;

            renderCurrentOrder(
                currentOrder,
                history
            );

            renderTimeline(
                history,
                currentOrder.order_id
            );

        } else {

            renderCurrentOrder(null);

            renderTimeline([], null);
        }

        // ============================================================
        // 6. Live sync indicator
        // ============================================================

        elements.syncText.textContent = 'Live 1.5s';

        elements.syncStatus.style.borderColor =
            'var(--border-subtle)';

    } catch (err) {

        console.error(
            'Polling error:',
            err
        );

        elements.syncText.textContent =
            'Sync delayed';

        elements.syncStatus.style.borderColor =
            'var(--warning-border)';

    } finally {

        state.isSyncing = false;

        state.isFirstPoll = false;
    }
}

  function updateOrderDropdown(orders) {
    if (!orders) return;

    const currentValue = elements.orderSelect.value;
    const existingOptions = new Set(Array.from(elements.orderSelect.options).map(o => o.value));

    orders.forEach(ord => {
      if (!existingOptions.has(ord.order_id)) {
        const opt = document.createElement('option');
        opt.value = ord.order_id;
        opt.textContent = `#${ord.order_id} — ${ord.product_name || ord.item_id}`;
        elements.orderSelect.appendChild(opt);
      }
    });

    if (currentValue && elements.orderSelect.querySelector(`option[value="${currentValue}"]`)) {
      elements.orderSelect.value = currentValue;
    }
  }

  // Click-to-view order from feed
  window.selectOrder = function(orderId) {
    if (!orderId) return;
    state.selectedOrderId = orderId;
    elements.orderSelect.value = orderId;
    pollCycle();
  };

  window.approveOrder = async function(orderId) {
    const res = await fetch(`${API_BASE}/orders/${encodeURIComponent(orderId)}/approve`, {
      method: 'POST',
    });
    const data = await res.json();
    if (!res.ok) {
      console.error('Approval failed:', data.detail || data);
      return;
    }
    pollCycle();
  };

  elements.orderSelect.addEventListener('change', (e) => {
    state.selectedOrderId = e.target.value;
    pollCycle();
  });

  elements.refreshBtn.addEventListener('click', () => {
    pollCycle();
  });

  elements.generateAuthorizationBtn.addEventListener('click', generateAuthorization);
  elements.savePolicyBtn.addEventListener('click', savePolicy);

  fetchActiveAuthorization()
    .then(renderAuthorization)
    .catch(error => console.error('Authorization lookup failed:', error));

  fetchActivePolicy()
    .then(renderPolicy)
    .catch(error => console.error('Policy lookup failed:', error));

  // Initial trigger & recurring 1.5s poll
  pollCycle();
  setInterval(pollCycle, 1500);

})();
