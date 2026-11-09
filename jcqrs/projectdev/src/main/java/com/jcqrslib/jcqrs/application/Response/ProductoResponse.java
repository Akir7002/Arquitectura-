package com.jcqrslib.jcqrs.application.Response;

import java.math.BigDecimal;

public class ProductoResponse {
    private int id;
    private String sku;
    private String nombre;
    private BigDecimal precio;
    private boolean activo;

    public int getId() { return id; }
    public void setId(int id) { this.id = id; }
    public String getSku() { return sku; }
    public void setSku(String sku) { this.sku = sku; }
    public String getNombre() { return nombre; }
    public void setNombre(String nombre) { this.nombre = nombre; }
    public BigDecimal getPrecio() { return precio; }
    public void setPrecio(BigDecimal precio) { this.precio = precio; }
    public boolean isActivo() { return activo; }
    public void setActivo(boolean activo) { this.activo = activo; }
}
