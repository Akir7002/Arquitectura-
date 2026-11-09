package com.jcqrslib.jcqrs.application.Command;

import org.springframework.stereotype.Service;

import com.jcqrslib.jcqrs.application.Request.ClientesDeleteRequest;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ClientesDeleteHandler implements IRequestHandler<ClientesDeleteRequest, Integer> {

    @Override
    public Integer handle(ClientesDeleteRequest request) {
        try {
            // Aquí se añade toda la lógica para producir el borrado de datos.
            System.out.println(request);            
            return 1;
        } catch (Exception ex) {
            return 0;
        }
    }

    @Override
    public Class<?> getRequestType() {
        return ClientesDeleteRequest.class;
    }    
}
