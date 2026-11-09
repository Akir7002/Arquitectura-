package com.jcqrslib.jcqrs.application.Query;

import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.ProductosByIdRequest;
import com.jcqrslib.jcqrs.application.Response.ProductoResponse;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ProductosByIdHandler implements IRequestHandler<ProductosByIdRequest, ProductoResponse> {
    private final InMemoryStore store;
    public ProductosByIdHandler(InMemoryStore store) { this.store = store; }
    public ProductoResponse handle(ProductosByIdRequest request) { return store.getProductos().get(request.getId()); }
    public Class<?> getRequestType() { return ProductosByIdRequest.class; }
}
