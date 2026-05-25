package com.literatureassistant.enums;

import lombok.Getter;

@Getter
public enum SessionStatus implements DbValueEnum {

    ACTIVE("active"),
    COMPLETED("completed"),
    EXPIRED("expired");

    private final String dbValue;

    SessionStatus(String dbValue) {
        this.dbValue = dbValue;
    }

    public static SessionStatus fromDbValue(String dbValue) {
        if (dbValue == null) {
            return null;
        }
        for (SessionStatus status : values()) {
            if (status.dbValue.equals(dbValue)) {
                return status;
            }
        }
        return null;
    }
}
