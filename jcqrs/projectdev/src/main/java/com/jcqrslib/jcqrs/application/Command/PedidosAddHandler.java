package com.jcqrslib.jcqrs.application.Command;

import java.math.BigDecimal;
import org.springframework.stereotype.Service;
import com.jcqrslib.jcqrs.application.Request.PedidosAddRequest;
import com.jcqrslib.jcqrs.application.Response.PedidoLineaResponse;
import com.jcqrslib.jcqrs.application.Response.PedidoResponse;
import com.jcqrslib.jcqrs.application.store.InMemoryStore;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class PedidosAddHandler implements IRequestHandler<PedidosAddRequest, Integer> {
    private final InMemoryStore store;
    public PedidosAddHandler(InMemoryStore store) { this.store = store; }
    public Integer handle(PedidosAddRequest request) {
        if (!store.clienteExists(request.getClienteId()) || request.getLineas() == null || request.getLineas().isEmpty()) return 0;
        var pedido = new PedidoResponse();
        pedido.setId(store.nextPedidoId());
        pedido.setClienteId(request.getClienteId());
        pedido.setEstado("BORRADOR");
        var total = BigDecimal.ZERO;
        for (var lineaRequest : request.getLineas()) {
            var producto = store.getProductos().get(lineaRequest.getProductoId());
            if (producto == null || !producto.isActivo() || lineaRequest.getCantidad() <= 0) return 0;
            var linea = new PedidoLineaResponse();
            linea.setProductoId(producto.getId());
            linea.setProducto(producto.getNombre());
            linea.setCantidad(lineaRequest.getCantidad());
            linea.setPrecioUnitario(producto.getPrecio());
            linea.setSubtotal(producto.getPrecio().multiply(BigDecimal.valueOf(lineaRequest.getCantidad())));
            pedido.getLineas().add(linea);
            total = total.add(linea.getSubtotal());
        }
        pedido.setTotal(total);
        store.getPedidos().put(pedido.getId(), pedido);
        return pedido.getId();
    }
    public Class<?> getRequestType() { return PedidosAddRequest.class; }
}
