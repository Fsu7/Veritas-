package com.literatureassistant.enums;

import lombok.Getter;

@Getter
public enum PreferredStyle {

    SIMPLE("simple", "通俗"),
    BALANCED("balanced", "均衡"),
    TECHNICAL("technical", "专业");

    private final String code;
    private final String label;

    PreferredStyle(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public static PreferredStyle fromCode(String code) {
        if (code == null) {
            return null;
        }
        for (PreferredStyle style : values()) {
            if (style.code.equals(code)) {
                return style;
            }
        }
        return null;
    }
}
