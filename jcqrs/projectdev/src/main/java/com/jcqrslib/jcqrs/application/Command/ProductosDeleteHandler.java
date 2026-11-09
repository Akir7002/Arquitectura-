package com.jcqrslib.jcqrs.application.Command;

import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.ProductosDeleteRequest;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ProductosDeleteHandler implements IRequestHandler<ProductosDeleteRequest, Integer> {
    private final InMemoryStore store;
    public ProductosDeleteHandler(InMemoryStore store) { this.store = store; }
    public Integer handle(ProductosDeleteRequest request) {
        if (!store.getProductos().containsKey(request.getId()) || store.pedidoUsesProducto(request.getId())) return 0;
        store.getProductos().remove(request.getId());
        return request.getId();
    }
    public Class<?> getRequestType() { return ProductosDeleteRequest.class; }
}
