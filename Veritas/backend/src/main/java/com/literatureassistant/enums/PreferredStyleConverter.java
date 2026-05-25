package com.literatureassistant.enums;

import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class PreferredStyleConverter extends AbstractEnumConverter<PreferredStyle> {

    public PreferredStyleConverter() {
        super(PreferredStyle.class);
    }
}
