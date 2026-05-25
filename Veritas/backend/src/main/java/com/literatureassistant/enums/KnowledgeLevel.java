package com.literatureassistant.enums;

import lombok.Getter;

@Getter
public enum KnowledgeLevel implements DbValueEnum {

    BEGINNER("beginner", "初级"),
    INTERMEDIATE("intermediate", "中级"),
    ADVANCED("advanced", "高级"),
    EXPERT("expert", "专家");

    private final String dbValue;
    private final String label;

    KnowledgeLevel(String dbValue, String label) {
        this.dbValue = dbValue;
        this.label = label;
    }

    public static KnowledgeLevel fromDbValue(String dbValue) {
        if (dbValue == null) {
            return null;
        }
        for (KnowledgeLevel level : values()) {
            if (level.dbValue.equals(dbValue)) {
                return level;
            }
        }
        return null;
    }
}
