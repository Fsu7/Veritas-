package com.literatureassistant.enums;

import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class SessionStatusConverter extends AbstractEnumConverter<SessionStatus> {

    public SessionStatusConverter() {
        super(SessionStatus.class);
    }
}
