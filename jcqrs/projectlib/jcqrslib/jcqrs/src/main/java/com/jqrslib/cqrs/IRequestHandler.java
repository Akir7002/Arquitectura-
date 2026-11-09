package com.jqrslib.cqrs;

/**
 * @author Ariel Alejandro Wagner
 * Interface for the requests that encapsulate the responses and implement 
 * the methods for handle() procesos.
 * 
 * Interface para las solicitudes que encapsulan las respuestas e implementa 
 * los métodos para para los procesos de handle().
 */
public interface IRequestHandler<TRequest extends IRequest<TResponse>, TResponse> {
    /**
     * Contain the principal logic. 
     * 
     * Contiene la lógica principal.
     * @param request Requests param. Parámetro de solictudes.
     * @return Responses return. Retorno de respuestas.
     */
    TResponse handle(TRequest request);

    /**
     * Indicates the type of class of requests handled.
     * 
     * Indica qué tipo de solicitud maneja la clase.
     * @return Return a class type. Retorna un tipo de clase.
     */
    Class<?> getRequestType();

    /**
     * It allow that Mediator know if the handler can be process a specific 
     * request instance.
     * 
     * Permite al Mediator saber si el handler puede procesar una instancia de 
     * solicitud específica.
     * @param request Request param. Parámetro de solicitud. 
     * @return Boolean type return. Retorna un tipo booleano.
     */
    default boolean canHandle(Object request) {
        return getRequestType().isAssignableFrom(request.getClass());
    }
}