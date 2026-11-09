package com.jcqrslib.jcqrs.cqrs;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * This class implement the mediator from class Mediator.
 * 
 * Esta clase implementa la clase mediador desde Mediator.
 */
@Component
public class Mediator {
    @Autowired
    private ApplicationContext context;

    /**
     * The function sends requests and returns data using an output response data type.
     * 
     * La función envía solicitudes y devuelve datos utilizando un tipo de datos de respuesta de salida.
     * @param <TRequest> Request - Solicitud
     * @param <TResponse> Response - Respuesta
     * @param request Request parameter. Parámetro de solicitud
     * @return Data return. Retorna los datos.
     */
    public <TRequest extends IRequest<TResponse>, TResponse> TResponse send(TRequest request) {
        Map<String, IRequestHandler> beans = context.getBeansOfType(IRequestHandler.class);

        for (IRequestHandler handler : beans.values()) {
            if (handler.canHandle(request)) {
                return ((IRequestHandler<TRequest, TResponse>) handler).handle(request);
            }
        }

        throw new RuntimeException("No se encontró un handler que pueda procesar: " + request.getClass().getSimpleName());
    }
}
