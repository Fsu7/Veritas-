package com.literatureassistant.enums;

import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class AnalysisTypeConverter extends AbstractEnumConverter<AnalysisType> {

    public AnalysisTypeConverter() {
        super(AnalysisType.class);
    }
}
