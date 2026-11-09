package com.jcqrslib.jcqrs.controller;

import java.util.ArrayList;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.jcqrslib.jcqrs.application.Request.*;
import com.jcqrslib.jcqrs.application.Response.ProductoResponse;
import com.jcqrslib.jcqrs.cqrs.Mediator;

@RestController
@RequestMapping("/productos")
public class ProductosController {
    private final Mediator mediator;
    public ProductosController(Mediator mediator) { this.mediator = mediator; }
    @GetMapping public ResponseEntity<ArrayList<ProductoResponse>> getAll() { return ResponseEntity.ok(mediator.send(new ProductosAllRequest())); }
    @GetMapping("/{id}") public ResponseEntity<ProductoResponse> getById(@PathVariable int id) {
        var response = mediator.send(new ProductosByIdRequest(id));
        return response == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(response);
    }
    @PostMapping("/add") public ResponseEntity<Integer> add(@RequestBody ProductosAddRequest request) {
        var id = mediator.send(request);
        return id == 0 ? ResponseEntity.badRequest().build() : ResponseEntity.status(HttpStatus.CREATED).body(id);
    }
    @PutMapping("/update") public ResponseEntity<Integer> update(@RequestBody ProductosUpdateRequest request) {
        var id = mediator.send(request);
        return id == 0 ? ResponseEntity.badRequest().build() : ResponseEntity.ok(id);
    }
    @DeleteMapping("/delete/{id}") public ResponseEntity<Integer> delete(@PathVariable int id) {
        var deleted = mediator.send(new ProductosDeleteRequest(id));
        return deleted == 0 ? ResponseEntity.badRequest().build() : ResponseEntity.noContent().build();
    }
}
