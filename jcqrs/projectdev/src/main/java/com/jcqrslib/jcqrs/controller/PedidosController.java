package com.jcqrslib.jcqrs.controller;

import java.util.ArrayList;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.jcqrslib.jcqrs.application.Request.*;
import com.jcqrslib.jcqrs.application.Response.PedidoResponse;
import com.jcqrslib.jcqrs.cqrs.Mediator;

@RestController
@RequestMapping("/pedidos")
public class PedidosController {
    private final Mediator mediator;
    public PedidosController(Mediator mediator) { this.mediator = mediator; }
    @GetMapping public ResponseEntity<ArrayList<PedidoResponse>> getAll() { return ResponseEntity.ok(mediator.send(new PedidosAllRequest())); }
    @GetMapping("/{id}") public ResponseEntity<PedidoResponse> getById(@PathVariable int id) {
        var response = mediator.send(new PedidosByIdRequest(id));
        return response == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(response);
    }
    @PostMapping("/add") public ResponseEntity<Integer> add(@RequestBody PedidosAddRequest request) {
        var id = mediator.send(request);
        return id == 0 ? ResponseEntity.badRequest().build() : ResponseEntity.status(HttpStatus.CREATED).body(id);
    }
    @DeleteMapping("/delete/{id}") public ResponseEntity<Integer> delete(@PathVariable int id) {
        var deleted = mediator.send(new PedidosDeleteRequest(id));
        return deleted == 0 ? ResponseEntity.badRequest().build() : ResponseEntity.noContent().build();
    }
}
