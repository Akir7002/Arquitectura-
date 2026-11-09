package com.jcqrslib.jcqrs.application.Query;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;

import com.jcqrslib.jcqrs.application.Request.ClientesByIdRequest;
import com.jcqrslib.jcqrs.application.Response.ClientesResponse;
import com.jcqrslib.jcqrs.cqrs.IRequestHandler;

@Service
public class ClientesByIdHandler implements IRequestHandler<ClientesByIdRequest, ClientesResponse> {

    @Override
    public ClientesResponse handle(ClientesByIdRequest request) {
        try {
            var lstClie = new ArrayList<ClientesResponse>();

            // 1
            var clie1 = new ClientesResponse();
            clie1.setId(1);
            clie1.setRazon("SOLITUX SRL");
            clie1.setDireccion("Av. San Juan 1234");
            clie1.setEmail("ventas@solutixsrl.com.ar");
            clie1.setMovil("11-4422-7755");
            lstClie.add(clie1);
            // 2
            var clie2 = new ClientesResponse();
            clie2.setId(2);
            clie2.setRazon("GRUPO TEXTIL SA");
            clie2.setDireccion("Rosario 7788");
            clie2.setEmail("info@grupo-textil.com.ar");
            clie2.setMovil("11-3344-9911");
            lstClie.add(clie2);
            // 3
            var clie3 = new ClientesResponse();
            clie3.setId(3);
            clie3.setRazon("ALUMINIUN METAL CO. SACIF");
            clie3.setDireccion("Triunvirato 8293");
            clie3.setEmail("info@aluminiummetal.com.ar");
            clie3.setMovil("11-3322-4275");
            lstClie.add(clie3);

            clie1 = null;
            clie2 = null;
            clie3 = null;

            List<ClientesResponse> result = lstClie.stream()
                    .filter(p -> p.getId() == request.getId())
                    .collect(Collectors.toList());

            return result.get(0);
        } catch (Exception ex) {
            return null;
        }
    }

    @Override
    public Class<?> getRequestType() {
        return ClientesByIdRequest.class;
    }
}
