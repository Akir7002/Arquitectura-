package com.jcqrslib.jcqrs.application.Query;

import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.PedidosByIdRequest;
import com.jcqrslib.jcqrs.application.Response.PedidoResponse;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class PedidosByIdHandler implements IRequestHandler<PedidosByIdRequest, PedidoResponse> {
    private final InMemoryStore store;
    public PedidosByIdHandler(InMemoryStore store) { this.store = store; }
    public PedidoResponse handle(PedidosByIdRequest request) { return store.getPedidos().get(request.getId()); }
    public Class<?> getRequestType() { return PedidosByIdRequest.class; }
}
