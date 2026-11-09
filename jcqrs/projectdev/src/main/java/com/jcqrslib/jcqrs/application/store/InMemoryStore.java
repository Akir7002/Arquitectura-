package com.jcqrslib.jcqrs.application.store;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

import org.springframework.stereotype.Component;

import com.jcqrslib.jcqrs.application.Response.PedidoResponse;
import com.jcqrslib.jcqrs.application.Response.ProductoResponse;

@Component
public class InMemoryStore {
    private final Map<Integer, ProductoResponse> productos = new ConcurrentHashMap<>();
    private final Map<Integer, PedidoResponse> pedidos = new ConcurrentHashMap<>();
    private final AtomicInteger nextProductoId = new AtomicInteger(1);
    private final AtomicInteger nextPedidoId = new AtomicInteger(1);

    public InMemoryStore() {
        addProducto("SKU-001", "Teclado mecanico", new BigDecimal("45.00"));
        addProducto("SKU-002", "Mouse inalambrico", new BigDecimal("25.00"));
    }

    public Map<Integer, ProductoResponse> getProductos() {
        return productos;
    }

    public Map<Integer, PedidoResponse> getPedidos() {
        return pedidos;
    }

    public int nextProductoId() {
        return nextProductoId.getAndIncrement();
    }

    public int nextPedidoId() {
        return nextPedidoId.getAndIncrement();
    }

    private void addProducto(String sku, String nombre, BigDecimal precio) {
        var producto = new ProductoResponse();
        producto.setId(nextProductoId());
        producto.setSku(sku);
        producto.setNombre(nombre);
        producto.setPrecio(precio);
        producto.setActivo(true);
        productos.put(producto.getId(), producto);
    }

    public boolean pedidoUsesProducto(int productoId) {
        return pedidos.values().stream()
                .flatMap(pedido -> pedido.getLineas().stream())
                .anyMatch(linea -> linea.getProductoId() == productoId);
    }

    public boolean clienteExists(int clienteId) {
        return clienteId >= 1 && clienteId <= 3;
    }

    public ArrayList<ProductoResponse> productos() {
        return new ArrayList<>(productos.values());
    }

    public ArrayList<PedidoResponse> pedidos() {
        return new ArrayList<>(pedidos.values());
    }
}
