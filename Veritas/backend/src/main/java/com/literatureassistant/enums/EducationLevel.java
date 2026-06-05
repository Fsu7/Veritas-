package com.literatureassistant.enums;

import lombok.Getter;

@Getter
public enum EducationLevel implements DbValueEnum {

    UNDERGRADUATE("undergraduate", "本科"),
    MASTER("master", "硕士"),
    PHD("phd", "博士"),
    FACULTY("faculty", "教师");

    private final String dbValue;
    private final String label;

    EducationLevel(String dbValue, String label) {
        this.dbValue = dbValue;
        this.label = label;
    }

    public static EducationLevel fromDbValue(String dbValue) {
        if (dbValue == null) {
            return null;
        }
        for (EducationLevel level : values()) {
            if (level.dbValue.equals(dbValue)) {
                return level;
            }
        }
        return null;
    }

    @Override
    public String toString() {
        return dbValue;
    }
}
