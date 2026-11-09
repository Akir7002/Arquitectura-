package com.jcqrslib.jcqrs.application.Request;

import com.jcqrslib.jcqrs.cqrs.IRequest;

public class ClientesDeleteRequest implements IRequest<Integer> {
    public int id;
    
    public ClientesDeleteRequest() {}

    public ClientesDeleteRequest(int _id) {
        this.id = _id;
    }    
    
    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }  
}
