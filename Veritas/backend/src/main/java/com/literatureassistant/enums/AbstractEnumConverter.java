package com.literatureassistant.enums;

import jakarta.persistence.AttributeConverter;

import java.util.Arrays;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

public abstract class AbstractEnumConverter<E extends Enum<E> & DbValueEnum>
        implements AttributeConverter<E, String> {

    private final Class<E> enumClass;
    private final Map<String, E> dbValueMap;

    protected AbstractEnumConverter(Class<E> enumClass) {
        this.enumClass = enumClass;
        this.dbValueMap = Arrays.stream(enumClass.getEnumConstants())
                .collect(Collectors.toMap(DbValueEnum::getDbValue, Function.identity()));
    }

    @Override
    public String convertToDatabaseColumn(E attribute) {
        if (attribute == null) {
            return null;
        }
        return attribute.getDbValue();
    }

    @Override
    public E convertToEntityAttribute(String dbData) {
        if (dbData == null) {
            return null;
        }
        E result = dbValueMap.get(dbData);
        if (result == null) {
            throw new IllegalArgumentException(
                    "Unknown dbValue '" + dbData + "' for enum " + enumClass.getSimpleName());
        }
        return result;
    }
}
