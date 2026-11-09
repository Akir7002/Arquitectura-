package com.jcqrslib.jcqrs.application.Request;

import com.jcqrslib.jcqrs.application.Response.ClientesResponse;
import com.jcqrslib.jcqrs.cqrs.IRequest;

public class ClientesByIdRequest implements IRequest<ClientesResponse> {
    public int id;

    public ClientesByIdRequest() {
    }

    public ClientesByIdRequest(int _id) {
        this.id = _id;
    }

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }
}
