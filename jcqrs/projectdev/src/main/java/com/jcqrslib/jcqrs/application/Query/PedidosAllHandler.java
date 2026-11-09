package com.jcqrslib.jcqrs.application.Query;

import java.util.ArrayList;
import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.PedidosAllRequest;
import com.jcqrslib.jcqrs.application.Response.PedidoResponse;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class PedidosAllHandler implements IRequestHandler<PedidosAllRequest, ArrayList<PedidoResponse>> {
    private final InMemoryStore store;
    public PedidosAllHandler(InMemoryStore store) { this.store = store; }
    public ArrayList<PedidoResponse> handle(PedidosAllRequest request) { return store.pedidos(); }
    public Class<?> getRequestType() { return PedidosAllRequest.class; }
}
