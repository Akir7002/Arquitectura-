package com.jcqrslib.jcqrs.application.Request;

import com.jcqrslib.jcqrs.application.Response.ProductoResponse;
import com.jcqrslib.jcqrs.cqrs.IRequest;

public class ProductosByIdRequest implements IRequest<ProductoResponse> {
    private int id;
    public ProductosByIdRequest() {}
    public ProductosByIdRequest(int id) { this.id = id; }
    public int getId() { return id; }
    public void setId(int id) { this.id = id; }
}
