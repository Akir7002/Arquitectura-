package com.jcqrslib.jcqrs.cqrs;

/**
 * This interface defines the business logic for the handlers for each type of request. Each 
 * class that implements this interface will be responsible for handling a specific request.
 * 
 * Esta interface define la lógica de negocio de los "handlers" o manejadores para cada tipo 
 * de solicitud. Cada clase que implemente esta interface se encargará de resolver una 
 * solicitud concreta.
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
