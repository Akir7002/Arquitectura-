package com.jcqrslib.jcqrs.application.Command;

import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.ProductosUpdateRequest;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ProductosUpdateHandler implements IRequestHandler<ProductosUpdateRequest, Integer> {
    private final InMemoryStore store;
    public ProductosUpdateHandler(InMemoryStore store) { this.store = store; }
    public Integer handle(ProductosUpdateRequest request) {
        var producto = store.getProductos().get(request.getId());
        if (producto == null || request.getSku() == null || request.getSku().isBlank() || request.getNombre() == null
                || request.getNombre().isBlank() || request.getPrecio() == null || request.getPrecio().signum() <= 0
                || store.getProductos().values().stream().anyMatch(p -> p.getId() != request.getId()
                        && p.getSku().equalsIgnoreCase(request.getSku()))) return 0;
        producto.setSku(request.getSku());
        producto.setNombre(request.getNombre());
        producto.setPrecio(request.getPrecio());
        return producto.getId();
    }
    public Class<?> getRequestType() { return ProductosUpdateRequest.class; }
}
