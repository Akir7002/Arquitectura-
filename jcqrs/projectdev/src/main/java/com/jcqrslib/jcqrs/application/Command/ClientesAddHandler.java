package com.jcqrslib.jcqrs.application.Command;

import org.springframework.stereotype.Service;

import com.jcqrslib.jcqrs.application.Request.ClientesAddRequest;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ClientesAddHandler implements IRequestHandler<ClientesAddRequest, Integer> {

    @Override
    public Integer handle(ClientesAddRequest request) {
        try {
            // Aquí se añade toda la lógica para producir el alta.
            System.out.println(request);            
            return 1;
        } catch (Exception ex) {
            return 0;
        }
    }

    @Override
    public Class<?> getRequestType() {
        return ClientesAddRequest.class;
    }    
}
