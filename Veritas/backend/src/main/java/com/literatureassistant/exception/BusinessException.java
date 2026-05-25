package com.literatureassistant.exception;

import lombok.Getter;

@Getter
public class BusinessException extends RuntimeException {

    private final int code;
    private final String errorKey;

    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
        this.errorKey = "";
    }

    public BusinessException(int code, String message, String errorKey) {
        super(message);
        this.code = code;
        this.errorKey = errorKey;
    }

    public BusinessException(int code, String message, Throwable cause) {
        super(message, cause);
        this.code = code;
        this.errorKey = "";
    }

    public BusinessException(int code, String message, Throwable cause, String errorKey) {
        super(message, cause);
        this.code = code;
        this.errorKey = errorKey;
    }
}
