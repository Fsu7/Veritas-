package com.literatureassistant.enums;

import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class AnalysisStatusConverter extends AbstractEnumConverter<AnalysisStatus> {

    public AnalysisStatusConverter() {
        super(AnalysisStatus.class);
    }
}
