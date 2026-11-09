package com.jcqrslib.jcqrs.application.Request;

import com.jcqrslib.jcqrs.cqrs.IRequest;

public class PedidosDeleteRequest implements IRequest<Integer> {
    private int id;
    public PedidosDeleteRequest() {}
    public PedidosDeleteRequest(int id) { this.id = id; }
    public int getId() { return id; }
    public void setId(int id) { this.id = id; }
}
