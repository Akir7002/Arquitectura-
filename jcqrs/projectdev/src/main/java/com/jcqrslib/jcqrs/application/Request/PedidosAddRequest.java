package com.jcqrslib.jcqrs.application.Request;

import java.util.ArrayList;
import com.jcqrslib.jcqrs.cqrs.IRequest;

public class PedidosAddRequest implements IRequest<Integer> {
    private int clienteId;
    private ArrayList<PedidoLineaRequest> lineas = new ArrayList<>();
    public int getClienteId() { return clienteId; }
    public void setClienteId(int clienteId) { this.clienteId = clienteId; }
    public ArrayList<PedidoLineaRequest> getLineas() { return lineas; }
    public void setLineas(ArrayList<PedidoLineaRequest> lineas) { this.lineas = lineas; }
}
