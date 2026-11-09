package com.jcqrslib.jcqrs.application.Request;

import java.util.ArrayList;
import com.jcqrslib.jcqrs.application.Response.ProductoResponse;
import com.jcqrslib.jcqrs.cqrs.IRequest;

public class ProductosAllRequest implements IRequest<ArrayList<ProductoResponse>> {}
