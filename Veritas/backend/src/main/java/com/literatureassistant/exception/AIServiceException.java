package com.literatureassistant.exception;

public class AIServiceException extends BusinessException {

    public AIServiceException(String message, Throwable cause) {
        super(503, message, cause, "AI_SERVICE_ERROR");
    }
}
