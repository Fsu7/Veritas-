package com.literatureassistant.enums;

import lombok.Getter;

@Getter
public enum KnowledgeLevel {

    BEGINNER("beginner", "初级"),
    INTERMEDIATE("intermediate", "中级"),
    ADVANCED("advanced", "高级"),
    EXPERT("expert", "专家");

    private final String code;
    private final String label;

    KnowledgeLevel(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public static KnowledgeLevel fromCode(String code) {
        if (code == null) {
            return null;
        }
        for (KnowledgeLevel level : values()) {
            if (level.code.equals(code)) {
                return level;
            }
        }
        return null;
    }
}
