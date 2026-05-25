package com.literatureassistant.enums;

import lombok.Getter;

@Getter
public enum EducationLevel {

    UNDERGRADUATE("undergraduate", "本科"),
    MASTER("master", "硕士"),
    PHD("phd", "博士"),
    FACULTY("faculty", "教师");

    private final String code;
    private final String label;

    EducationLevel(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public static EducationLevel fromCode(String code) {
        if (code == null) {
            return null;
        }
        for (EducationLevel level : values()) {
            if (level.code.equals(code)) {
                return level;
            }
        }
        return null;
    }
}
