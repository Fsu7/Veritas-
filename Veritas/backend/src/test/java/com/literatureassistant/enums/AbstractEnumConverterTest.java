package com.literatureassistant.enums;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class AbstractEnumConverterTest {

    private AnalysisStatusConverter converter;

    @BeforeEach
    void setUp() {
        converter = new AnalysisStatusConverter();
    }

    @Nested
    @DisplayName("convertToDatabaseColumn: Java枚举 → 数据库值")
    class ConvertToDatabaseColumn {

        @Test
        @DisplayName("PENDING → 'pending'")
        void pendingToLowercase() {
            assertEquals("pending", converter.convertToDatabaseColumn(AnalysisStatus.PENDING));
        }

        @Test
        @DisplayName("PROCESSING → 'processing'")
        void processingToLowercase() {
            assertEquals("processing", converter.convertToDatabaseColumn(AnalysisStatus.PROCESSING));
        }

        @Test
        @DisplayName("COMPLETED → 'completed'")
        void completedToLowercase() {
            assertEquals("completed", converter.convertToDatabaseColumn(AnalysisStatus.COMPLETED));
        }

        @Test
        @DisplayName("FAILED → 'failed'")
        void failedToLowercase() {
            assertEquals("failed", converter.convertToDatabaseColumn(AnalysisStatus.FAILED));
        }

        @Test
        @DisplayName("null → null")
        void nullReturnsNull() {
            assertNull(converter.convertToDatabaseColumn(null));
        }
    }

    @Nested
    @DisplayName("convertToEntityAttribute: 数据库值 → Java枚举")
    class ConvertToEntityAttribute {

        @Test
        @DisplayName("'pending' → PENDING")
        void pendingToEnum() {
            assertEquals(AnalysisStatus.PENDING, converter.convertToEntityAttribute("pending"));
        }

        @Test
        @DisplayName("'processing' → PROCESSING")
        void processingToEnum() {
            assertEquals(AnalysisStatus.PROCESSING, converter.convertToEntityAttribute("processing"));
        }

        @Test
        @DisplayName("'completed' → COMPLETED")
        void completedToEnum() {
            assertEquals(AnalysisStatus.COMPLETED, converter.convertToEntityAttribute("completed"));
        }

        @Test
        @DisplayName("'failed' → FAILED")
        void failedToEnum() {
            assertEquals(AnalysisStatus.FAILED, converter.convertToEntityAttribute("failed"));
        }

        @Test
        @DisplayName("null → null")
        void nullReturnsNull() {
            assertNull(converter.convertToEntityAttribute(null));
        }

        @Test
        @DisplayName("未知值抛出IllegalArgumentException")
        void unknownValueThrows() {
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> converter.convertToEntityAttribute("unknown"));
            assertTrue(ex.getMessage().contains("unknown"));
            assertTrue(ex.getMessage().contains("AnalysisStatus"));
        }

        @Test
        @DisplayName("大写值无法匹配（严格小写）")
        void uppercaseNotMatched() {
            assertThrows(IllegalArgumentException.class,
                    () -> converter.convertToEntityAttribute("PENDING"));
        }
    }

    @Nested
    @DisplayName("双向转换一致性")
    class RoundTrip {

        @Test
        @DisplayName("所有枚举值 round-trip 一致")
        void allValuesRoundTrip() {
            for (AnalysisStatus status : AnalysisStatus.values()) {
                String dbValue = converter.convertToDatabaseColumn(status);
                AnalysisStatus restored = converter.convertToEntityAttribute(dbValue);
                assertSame(status, restored,
                        status.name() + " round-trip failed");
            }
        }
    }
}
