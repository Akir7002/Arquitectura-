package com.jcqrslib.jcqrs.application.Request;

import com.jcqrslib.jcqrs.cqrs.IRequest;

public class ClientesAddRequest implements IRequest<Integer> {
    public String razon;
    public String direccion;
    public String email;
    public String movil;
    
    public ClientesAddRequest() {}

    public String getRazon() {
        return razon;
    }

    public void setRazon(String razon) {
        this.razon = razon;
    }

    public String getDireccion() {
        return direccion;
    }

    public void setDireccion(String direccion) {
        this.direccion = direccion;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getMovil() {
        return movil;
    }

    public void setMovil(String movil) {
        this.movil = movil;
    }      
}
