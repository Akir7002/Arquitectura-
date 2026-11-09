package com.jcqrslib.jcqrs.application.Command;

import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.PedidosDeleteRequest;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class PedidosDeleteHandler implements IRequestHandler<PedidosDeleteRequest, Integer> {
    private final InMemoryStore store;
    public PedidosDeleteHandler(InMemoryStore store) { this.store = store; }
    public Integer handle(PedidosDeleteRequest request) {
        var pedido = store.getPedidos().get(request.getId());
        if (pedido == null || !"BORRADOR".equals(pedido.getEstado())) return 0;
        store.getPedidos().remove(request.getId());
        return request.getId();
    }
    public Class<?> getRequestType() { return PedidosDeleteRequest.class; }
}
