package com.jcqrslib.jcqrs.application.Command;

import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.ProductosAddRequest;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ProductosAddHandler implements IRequestHandler<ProductosAddRequest, Integer> {
    private final InMemoryStore store;
    public ProductosAddHandler(InMemoryStore store) { this.store = store; }
    public Integer handle(ProductosAddRequest request) {
        if (request.getSku() == null || request.getSku().isBlank() || request.getNombre() == null
                || request.getNombre().isBlank() || request.getPrecio() == null
                || request.getPrecio().signum() <= 0
                || store.getProductos().values().stream().anyMatch(p -> p.getSku().equalsIgnoreCase(request.getSku()))) {
            return 0;
        }
        var producto = new com.jcqrslib.jcqrs.application.Response.ProductoResponse();
        producto.setId(store.nextProductoId());
        producto.setSku(request.getSku());
        producto.setNombre(request.getNombre());
        producto.setPrecio(request.getPrecio());
        producto.setActivo(true);
        store.getProductos().put(producto.getId(), producto);
        return producto.getId();
    }
    public Class<?> getRequestType() { return ProductosAddRequest.class; }
}
