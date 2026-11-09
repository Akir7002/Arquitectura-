package com.jcqrslib.jcqrs.application.Command;

import org.springframework.stereotype.Service;

import com.jcqrslib.jcqrs.application.Request.ClientesUpdateRequest;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ClientesUpdateHandler implements IRequestHandler<ClientesUpdateRequest, Integer> {

    @Override
    public Integer handle(ClientesUpdateRequest request) {
        try {
            // Aquí se añade toda la lógica para producir la actualización de datos.
            System.out.println(request);            
            return 1;
        } catch (Exception ex) {
            return 0;
        }
    }

    @Override
    public Class<?> getRequestType() {
        return ClientesUpdateRequest.class;
    }
}
