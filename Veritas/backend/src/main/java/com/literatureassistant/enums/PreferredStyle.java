package com.literatureassistant.enums;

import lombok.Getter;

@Getter
public enum PreferredStyle implements DbValueEnum {

    SIMPLE("simple", "通俗"),
    BALANCED("balanced", "均衡"),
    TECHNICAL("technical", "专业");

    private final String dbValue;
    private final String label;

    PreferredStyle(String dbValue, String label) {
        this.dbValue = dbValue;
        this.label = label;
    }

    public static PreferredStyle fromDbValue(String dbValue) {
        if (dbValue == null) {
            return null;
        }
        for (PreferredStyle style : values()) {
            if (style.dbValue.equals(dbValue)) {
                return style;
            }
        }
        return null;
    }
}
