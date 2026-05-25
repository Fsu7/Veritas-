package com.literatureassistant.exception;

public class AuthenticationException extends BusinessException {

    public AuthenticationException(String message) {
        super(401, message, "AUTHENTICATION_FAILED");
    }
}
