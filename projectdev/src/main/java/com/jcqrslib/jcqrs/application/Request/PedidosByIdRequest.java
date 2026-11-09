package com.jcqrslib.jcqrs.application.Request;

import com.jcqrslib.jcqrs.application.Response.PedidoResponse;
import com.jcqrslib.jcqrs.cqrs.IRequest;

public class PedidosByIdRequest implements IRequest<PedidoResponse> {
    private int id;
    public PedidosByIdRequest() {}
    public PedidosByIdRequest(int id) { this.id = id; }
    public int getId() { return id; }
    public void setId(int id) { this.id = id; }
}
