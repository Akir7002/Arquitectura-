package com.jcqrslib.jcqrs.application.Query;

import java.util.ArrayList;
import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.ProductosAllRequest;
import com.jcqrslib.jcqrs.application.Response.ProductoResponse;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ProductosAllHandler implements IRequestHandler<ProductosAllRequest, ArrayList<ProductoResponse>> {
    private final InMemoryStore store;
    public ProductosAllHandler(InMemoryStore store) { this.store = store; }
    public ArrayList<ProductoResponse> handle(ProductosAllRequest request) { return store.productos(); }
    public Class<?> getRequestType() { return ProductosAllRequest.class; }
}
