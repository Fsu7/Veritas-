package com.literatureassistant.enums;

import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class EducationLevelConverter extends AbstractEnumConverter<EducationLevel> {

    public EducationLevelConverter() {
        super(EducationLevel.class);
    }
}
