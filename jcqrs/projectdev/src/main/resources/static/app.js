const state = { clients: [], products: [], orders: [] };

async function request(path, options) {
    const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
    if (!response.ok) throw new Error(`La solicitud fallo (${response.status})`);
    return response.status === 204 ? null : response.json();
}

function showMessage(text, error = false) {
    const element = document.querySelector("#message");
    element.textContent = text;
    element.classList.toggle("error", error);
    element.hidden = false;
    setTimeout(() => { element.hidden = true; }, 3500);
}

function renderProducts() {
    document.querySelector("#product-count").textContent = state.products.filter(p => p.activo).length;
    document.querySelector("#product-select").innerHTML = state.products
        .filter(p => p.activo)
        .map(p => `<option value="${p.id}">${p.nombre} - $${Number(p.precio).toFixed(2)}</option>`).join("");
    document.querySelector("#products").innerHTML = state.products.length
        ? `<table><thead><tr><th>SKU</th><th>Producto</th><th>Precio</th><th>Estado</th></tr></thead><tbody>${state.products.map(p =>
            `<tr><td>${p.sku}</td><td>${p.nombre}</td><td>$${Number(p.precio).toFixed(2)}</td><td><span class="status">${p.activo ? "Activo" : "Inactivo"}</span></td></tr>`).join("")}</tbody></table>`
        : `<p class="empty">No hay productos.</p>`;
}

function renderClients() {
    document.querySelector("#client-count").textContent = state.clients.length;
    document.querySelector("#client-select").innerHTML = state.clients.map(c => `<option value="${c.id}">${c.razon}</option>`).join("");
}

function renderOrders() {
    document.querySelector("#order-count").textContent = state.orders.length;
    document.querySelector("#orders").innerHTML = state.orders.length
        ? state.orders.slice().reverse().map(order => `<div class="order"><div class="order-head"><strong>Pedido #${order.id}</strong><span class="status">${order.estado}</span></div><small>Cliente ${order.clienteId} · ${order.lineas.length} linea(s) · Total $${Number(order.total).toFixed(2)}</small></div>`).join("")
        : `<p class="empty">Todavia no hay pedidos.</p>`;
}

async function load() {
    try {
        [state.clients, state.products, state.orders] = await Promise.all([request("/clientes"), request("/productos"), request("/pedidos")]);
        renderClients(); renderProducts(); renderOrders();
    } catch (error) { showMessage(error.message, true); }
}

document.querySelector("#open-product-form").addEventListener("click", () => {
    const form = document.querySelector("#product-form");
    form.hidden = !form.hidden;
});

document.querySelector("#product-create-form").addEventListener("submit", async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    data.precio = Number(data.precio);
    try { await request("/productos/add", { method: "POST", body: JSON.stringify(data) }); event.target.reset(); showMessage("Producto creado."); await load(); }
    catch (error) { showMessage(error.message, true); }
});

document.querySelector("#order-form").addEventListener("submit", async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    data.clienteId = Number(data.clienteId);
    data.lineas = [{ productoId: Number(data.productoId), cantidad: Number(data.cantidad) }];
    delete data.productoId; delete data.cantidad;
    try { await request("/pedidos/add", { method: "POST", body: JSON.stringify(data) }); showMessage("Pedido creado."); await load(); }
    catch (error) { showMessage(error.message, true); }
});

load();
