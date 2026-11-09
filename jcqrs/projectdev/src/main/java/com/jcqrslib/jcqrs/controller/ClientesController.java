package com.jcqrslib.jcqrs.controller;

import java.util.ArrayList;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.jcqrslib.jcqrs.application.Response.ClientesResponse;
import com.jcqrslib.jcqrs.application.Request.*;
import com.jcqrslib.jcqrs.cqrs.Mediator;

@RestController
@RequestMapping("/clientes")
public class ClientesController {
    @Autowired
    Mediator _mediator;

    @GetMapping
    public ResponseEntity<ArrayList<ClientesResponse>> getAll() {
        var response = _mediator.send(new ClientesAllRequest());
        if (response == null)
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        return ResponseEntity.status(HttpStatus.OK).body(response);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ClientesResponse> getById(@PathVariable("id") int id) {
        var response = _mediator.send(new ClientesByIdRequest(id));
        if (response == null)
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        return ResponseEntity.status(HttpStatus.OK).body(response);
    }

    @PostMapping("/add")
    public ResponseEntity<Integer> add(@RequestBody ClientesAddRequest entity) {
        var response = _mediator.send(entity);
        if (response == 0) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @DeleteMapping("/delete/{id}")
    public ResponseEntity<Integer> delete(@PathVariable("id") int id) {
        var response = _mediator.send(new ClientesDeleteRequest(id));
        if (response == 0) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();
        }
        return ResponseEntity.status(HttpStatus.NO_CONTENT).body(response);
    }

    @PutMapping("/update")
    public ResponseEntity<Integer> update(@RequestBody ClientesUpdateRequest entity) {
        var response = _mediator.send(entity);
        if (response == 0) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }
}
