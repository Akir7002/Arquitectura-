package com.jcqrslib.jcqrs.application.Request;

import java.util.ArrayList;
import com.jcqrslib.jcqrs.application.Response.PedidoResponse;
import com.jcqrslib.jcqrs.cqrs.IRequest;

public class PedidosAllRequest implements IRequest<ArrayList<PedidoResponse>> {}
