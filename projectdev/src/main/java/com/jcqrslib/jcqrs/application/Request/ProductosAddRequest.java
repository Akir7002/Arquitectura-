package com.jcqrslib.jcqrs.application.Request;

import java.math.BigDecimal;
import com.jcqrslib.jcqrs.cqrs.IRequest;

public class ProductosAddRequest implements IRequest<Integer> {
    private String sku;
    private String nombre;
    private BigDecimal precio;
    public String getSku() { return sku; }
    public void setSku(String sku) { this.sku = sku; }
    public String getNombre() { return nombre; }
    public void setNombre(String nombre) { this.nombre = nombre; }
    public BigDecimal getPrecio() { return precio; }
    public void setPrecio(BigDecimal precio) { this.precio = precio; }
}
