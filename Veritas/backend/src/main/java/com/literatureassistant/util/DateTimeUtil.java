package com.literatureassistant.util;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public final class DateTimeUtil {

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private DateTimeUtil() {
    }

    public static String formatDateTime(LocalDateTime dateTime) {
        return dateTime.format(FORMATTER);
    }

    public static LocalDateTime parseDateTime(String dateTimeStr) {
        return LocalDateTime.parse(dateTimeStr, FORMATTER);
    }

    public static long getCurrentTimestamp() {
        return System.currentTimeMillis();
    }

    public static boolean isExpired(LocalDateTime dateTime) {
        return dateTime.isBefore(LocalDateTime.now());
    }
}
