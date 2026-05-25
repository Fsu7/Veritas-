package com.literatureassistant.enums;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class EnumConverterIntegrationTest {

    @Nested
    @DisplayName("AnalysisTypeConverter")
    class AnalysisTypeConverterTest {

        private AnalysisTypeConverter converter;

        @BeforeEach
        void setUp() {
            converter = new AnalysisTypeConverter();
        }

        @Test
        @DisplayName("PAPER_ANALYSIS ↔ 'paper_analysis'")
        void paperAnalysis() {
            assertEquals("paper_analysis", converter.convertToDatabaseColumn(AnalysisType.PAPER_ANALYSIS));
            assertEquals(AnalysisType.PAPER_ANALYSIS, converter.convertToEntityAttribute("paper_analysis"));
        }

        @Test
        @DisplayName("COMPARE ↔ 'compare'")
        void compare() {
            assertEquals("compare", converter.convertToDatabaseColumn(AnalysisType.COMPARE));
            assertEquals(AnalysisType.COMPARE, converter.convertToEntityAttribute("compare"));
        }

        @Test
        @DisplayName("REPORT ↔ 'report'")
        void report() {
            assertEquals("report", converter.convertToDatabaseColumn(AnalysisType.REPORT));
            assertEquals(AnalysisType.REPORT, converter.convertToEntityAttribute("report"));
        }

        @Test
        @DisplayName("round-trip一致性")
        void roundTrip() {
            for (AnalysisType type : AnalysisType.values()) {
                assertSame(type, converter.convertToEntityAttribute(
                        converter.convertToDatabaseColumn(type)));
            }
        }
    }

    @Nested
    @DisplayName("SessionStatusConverter")
    class SessionStatusConverterTest {

        private SessionStatusConverter converter;

        @BeforeEach
        void setUp() {
            converter = new SessionStatusConverter();
        }

        @Test
        @DisplayName("ACTIVE ↔ 'active'")
        void active() {
            assertEquals("active", converter.convertToDatabaseColumn(SessionStatus.ACTIVE));
            assertEquals(SessionStatus.ACTIVE, converter.convertToEntityAttribute("active"));
        }

        @Test
        @DisplayName("COMPLETED ↔ 'completed'")
        void completed() {
            assertEquals("completed", converter.convertToDatabaseColumn(SessionStatus.COMPLETED));
            assertEquals(SessionStatus.COMPLETED, converter.convertToEntityAttribute("completed"));
        }

        @Test
        @DisplayName("EXPIRED ↔ 'expired'")
        void expired() {
            assertEquals("expired", converter.convertToDatabaseColumn(SessionStatus.EXPIRED));
            assertEquals(SessionStatus.EXPIRED, converter.convertToEntityAttribute("expired"));
        }

        @Test
        @DisplayName("round-trip一致性")
        void roundTrip() {
            for (SessionStatus status : SessionStatus.values()) {
                assertSame(status, converter.convertToEntityAttribute(
                        converter.convertToDatabaseColumn(status)));
            }
        }
    }

    @Nested
    @DisplayName("EducationLevelConverter")
    class EducationLevelConverterTest {

        private EducationLevelConverter converter;

        @BeforeEach
        void setUp() {
            converter = new EducationLevelConverter();
        }

        @Test
        @DisplayName("UNDERGRADUATE ↔ 'undergraduate'")
        void undergraduate() {
            assertEquals("undergraduate", converter.convertToDatabaseColumn(EducationLevel.UNDERGRADUATE));
            assertEquals(EducationLevel.UNDERGRADUATE, converter.convertToEntityAttribute("undergraduate"));
        }

        @Test
        @DisplayName("MASTER ↔ 'master'")
        void master() {
            assertEquals("master", converter.convertToDatabaseColumn(EducationLevel.MASTER));
            assertEquals(EducationLevel.MASTER, converter.convertToEntityAttribute("master"));
        }

        @Test
        @DisplayName("PHD ↔ 'phd'")
        void phd() {
            assertEquals("phd", converter.convertToDatabaseColumn(EducationLevel.PHD));
            assertEquals(EducationLevel.PHD, converter.convertToEntityAttribute("phd"));
        }

        @Test
        @DisplayName("FACULTY ↔ 'faculty'")
        void faculty() {
            assertEquals("faculty", converter.convertToDatabaseColumn(EducationLevel.FACULTY));
            assertEquals(EducationLevel.FACULTY, converter.convertToEntityAttribute("faculty"));
        }

        @Test
        @DisplayName("round-trip一致性")
        void roundTrip() {
            for (EducationLevel level : EducationLevel.values()) {
                assertSame(level, converter.convertToEntityAttribute(
                        converter.convertToDatabaseColumn(level)));
            }
        }
    }

    @Nested
    @DisplayName("KnowledgeLevelConverter")
    class KnowledgeLevelConverterTest {

        private KnowledgeLevelConverter converter;

        @BeforeEach
        void setUp() {
            converter = new KnowledgeLevelConverter();
        }

        @Test
        @DisplayName("round-trip一致性")
        void roundTrip() {
            for (KnowledgeLevel level : KnowledgeLevel.values()) {
                assertSame(level, converter.convertToEntityAttribute(
                        converter.convertToDatabaseColumn(level)));
            }
        }

        @Test
        @DisplayName("BEGINNER ↔ 'beginner'")
        void beginner() {
            assertEquals("beginner", converter.convertToDatabaseColumn(KnowledgeLevel.BEGINNER));
            assertEquals(KnowledgeLevel.BEGINNER, converter.convertToEntityAttribute("beginner"));
        }
    }

    @Nested
    @DisplayName("PreferredStyleConverter")
    class PreferredStyleConverterTest {

        private PreferredStyleConverter converter;

        @BeforeEach
        void setUp() {
            converter = new PreferredStyleConverter();
        }

        @Test
        @DisplayName("round-trip一致性")
        void roundTrip() {
            for (PreferredStyle style : PreferredStyle.values()) {
                assertSame(style, converter.convertToEntityAttribute(
                        converter.convertToDatabaseColumn(style)));
            }
        }

        @Test
        @DisplayName("SIMPLE ↔ 'simple'")
        void simple() {
            assertEquals("simple", converter.convertToDatabaseColumn(PreferredStyle.SIMPLE));
            assertEquals(PreferredStyle.SIMPLE, converter.convertToEntityAttribute("simple"));
        }
    }
}
