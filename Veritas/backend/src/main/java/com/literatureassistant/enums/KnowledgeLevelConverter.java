package com.literatureassistant.enums;

import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class KnowledgeLevelConverter extends AbstractEnumConverter<KnowledgeLevel> {

    public KnowledgeLevelConverter() {
        super(KnowledgeLevel.class);
    }
}
