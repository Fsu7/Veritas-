package com.literatureassistant.enums;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

@Getter
public enum AnalysisType implements DbValueEnum {

    PAPER_ANALYSIS("paper_analysis"),
    COMPARE("compare"),
    REPORT("report");

    @JsonValue
    private final String dbValue;

    AnalysisType(String dbValue) {
        this.dbValue = dbValue;
    }

    public static AnalysisType fromDbValue(String dbValue) {
        if (dbValue == null) {
            return null;
        }
        for (AnalysisType type : values()) {
            if (type.dbValue.equals(dbValue)) {
                return type;
            }
        }
        return null;
    }

    @Override
    public String toString() {
        return dbValue;
    }
}
