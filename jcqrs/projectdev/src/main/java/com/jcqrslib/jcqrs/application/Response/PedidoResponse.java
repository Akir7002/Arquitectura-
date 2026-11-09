package com.jcqrslib.jcqrs.application.Response;

import java.math.BigDecimal;
import java.util.ArrayList;

public class PedidoResponse {
    private int id;
    private int clienteId;
    private String estado;
    private BigDecimal total;
    private ArrayList<PedidoLineaResponse> lineas = new ArrayList<>();

    public int getId() { return id; }
    public void setId(int id) { this.id = id; }
    public int getClienteId() { return clienteId; }
    public void setClienteId(int clienteId) { this.clienteId = clienteId; }
    public String getEstado() { return estado; }
    public void setEstado(String estado) { this.estado = estado; }
    public BigDecimal getTotal() { return total; }
    public void setTotal(BigDecimal total) { this.total = total; }
    public ArrayList<PedidoLineaResponse> getLineas() { return lineas; }
    public void setLineas(ArrayList<PedidoLineaResponse> lineas) { this.lineas = lineas; }
}
