package com.jcqrslib.jcqrs.application.Request;

import java.util.ArrayList;

import com.jcqrslib.jcqrs.application.Response.ClientesResponse;
import com.jcqrslib.jcqrs.cqrs.IRequest;

public class ClientesAllRequest implements IRequest<ArrayList<ClientesResponse>> {
}
