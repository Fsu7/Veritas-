package com.literatureassistant.enums;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

@Getter
public enum AnalysisStatus implements DbValueEnum {

    PENDING("pending"),
    PROCESSING("processing"),
    COMPLETED("completed"),
    FAILED("failed");

    @JsonValue
    private final String dbValue;

    AnalysisStatus(String dbValue) {
        this.dbValue = dbValue;
    }

    public static AnalysisStatus fromDbValue(String dbValue) {
        if (dbValue == null) {
            return null;
        }
        for (AnalysisStatus status : values()) {
            if (status.dbValue.equals(dbValue)) {
                return status;
            }
        }
        return null;
    }

    @Override
    public String toString() {
        return dbValue;
    }
}
