package com.literatureassistant.util;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;

class DateTimeUtilTest {

    @Test
    @DisplayName("formatDateTime should format LocalDateTime to yyyy-MM-dd HH:mm:ss")
    void shouldFormatDateTime() {
        LocalDateTime dateTime = LocalDateTime.of(2026, 5, 25, 14, 30, 45);
        String result = DateTimeUtil.formatDateTime(dateTime);
        assertEquals("2026-05-25 14:30:45", result);
    }

    @Test
    @DisplayName("parseDateTime should parse yyyy-MM-dd HH:mm:ss string to LocalDateTime")
    void shouldParseDateTime() {
        LocalDateTime result = DateTimeUtil.parseDateTime("2026-05-25 14:30:45");
        assertEquals(LocalDateTime.of(2026, 5, 25, 14, 30, 45), result);
    }

    @Test
    @DisplayName("formatDateTime and parseDateTime should be inverse operations")
    void shouldFormatAndParseBeInverse() {
        LocalDateTime original = LocalDateTime.of(2026, 5, 25, 14, 30, 45);
        String formatted = DateTimeUtil.formatDateTime(original);
        LocalDateTime parsed = DateTimeUtil.parseDateTime(formatted);
        assertEquals(original, parsed);
    }

    @Test
    @DisplayName("getCurrentTimestamp should return reasonable timestamp")
    void shouldReturnCurrentTimestamp() {
        long before = System.currentTimeMillis();
        long result = DateTimeUtil.getCurrentTimestamp();
        long after = System.currentTimeMillis();
        assertTrue(result >= before && result <= after);
    }

    @Test
    @DisplayName("isExpired should return true for past time")
    void shouldReturnTrueForExpiredTime() {
        LocalDateTime past = LocalDateTime.of(2020, 1, 1, 0, 0, 0);
        assertTrue(DateTimeUtil.isExpired(past));
    }

    @Test
    @DisplayName("isExpired should return false for future time")
    void shouldReturnFalseForFutureTime() {
        LocalDateTime future = LocalDateTime.of(2099, 12, 31, 23, 59, 59);
        assertFalse(DateTimeUtil.isExpired(future));
    }
}
