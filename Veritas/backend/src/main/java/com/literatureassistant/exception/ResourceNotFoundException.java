package com.literatureassistant.exception;

public class ResourceNotFoundException extends BusinessException {

    public ResourceNotFoundException(String resource, String id) {
        super(404, resource + " not found: " + id, "RESOURCE_NOT_FOUND");
    }
}
