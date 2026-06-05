package com.literatureassistant.dto;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.common.UserProfileDTO;
import com.literatureassistant.dto.response.AgentStateResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.ModelStatusDTO;
import com.literatureassistant.dto.response.PaperSearchResultDTO;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * AI DTO 序列化/反序列化/校验 单元测试。
 * <p>覆盖 6 个核心场景：AgentRequest 序列化/反序列化、AnalysisResultDTO 枚举映射、
 * AgentStateResponse 字段映射、UserProfileDTO 默认值、AgentRequest 校验。
 *
 * @author XH-202630 Literature Assistant
 */
class AiDtoSerializationTest {

    private static ObjectMapper objectMapper;
    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void setUp() {
        objectMapper = new ObjectMapper()
                .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                .enable(MapperFeature.ACCEPT_CASE_INSENSITIVE_ENUMS)
                .enable(SerializationFeature.WRITE_ENUMS_USING_TO_STRING)
                .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
                .registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void tearDown() {
        factory.close();
    }

    @Test
    @DisplayName("AgentRequest - 序列化为 snake_case JSON")
    void agentRequest_serialization_to_python_format() throws Exception {
        AgentRequest request = AgentRequest.builder()
                .topic("Multi-Agent协同决策")
                .paperIds(List.of("arxiv_2024_001"))
                .userId("usr_001")
                .userProfile(UserProfileDTO.builder()
                        .educationLevel(EducationLevel.MASTER)
                        .researchField("NLP")
                        .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                        .preferredStyle(PreferredStyle.BALANCED)
                        .build())
                .analysisType(AnalysisType.PAPER_ANALYSIS)
                .analysisId("anl_001")
                .build();

        String json = objectMapper.writeValueAsString(request);

        // 验证 snake_case 字段
        assertThat(json).contains("\"paper_ids\":[\"arxiv_2024_001\"]");
        assertThat(json).contains("\"user_id\":\"usr_001\"");
        assertThat(json).contains("\"user_profile\":");
        assertThat(json).contains("\"education_level\":\"master\"");
        assertThat(json).contains("\"research_field\":\"NLP\"");
        assertThat(json).contains("\"analysis_type\":\"paper_analysis\"");
        assertThat(json).contains("\"analysis_id\":\"anl_001\"");
    }

    @Test
    @DisplayName("AgentRequest - Python JSON 反序列化正确解析（snake_case 输入）")
    void agentRequest_deserialization_from_python() throws Exception {
        // Python 端 WebClient 用 snake_case 字段发送（依赖全局 SNAKE_CASE）
        String pythonJson = """
                {
                    "topic": "Multi-Agent协同决策",
                    "paper_ids": ["arxiv_2024_001"],
                    "user_id": "usr_001",
                    "user_profile": {
                        "education_level": "master",
                        "research_field": "NLP",
                        "knowledge_level": "intermediate",
                        "preferred_style": "balanced"
                    },
                    "analysis_type": "report",
                    "analysis_id": "anl_002"
                }
                """;

        AgentRequest request = objectMapper.readValue(pythonJson, AgentRequest.class);

        assertThat(request.getTopic()).isEqualTo("Multi-Agent协同决策");
        assertThat(request.getPaperIds()).containsExactly("arxiv_2024_001");
        assertThat(request.getUserId()).isEqualTo("usr_001");
        assertThat(request.getUserProfile().getEducationLevel()).isEqualTo(EducationLevel.MASTER);
        assertThat(request.getUserProfile().getKnowledgeLevel()).isEqualTo(KnowledgeLevel.INTERMEDIATE);
        assertThat(request.getUserProfile().getPreferredStyle()).isEqualTo(PreferredStyle.BALANCED);
        assertThat(request.getAnalysisType()).isEqualTo(AnalysisType.REPORT);
        assertThat(request.getAnalysisId()).isEqualTo("anl_002");
    }

    @Test
    @DisplayName("AnalysisResultDTO - status 枚举正确反序列化（completed/failed/degraded）")
    void analysisResultDTO_status_enum_mapping() throws Exception {
        for (AnalysisStatus status : AnalysisStatus.values()) {
            String json = """
                    {"analysis_id": "anl_x", "status": "%s", "degraded": false}
                    """.formatted(status.getDbValue());
            AnalysisResultDTO dto = objectMapper.readValue(json, AnalysisResultDTO.class);
            assertThat(dto.getStatus()).isEqualTo(status);
        }
    }

    @Test
    @DisplayName("AgentStateResponse - 5 字段正确反序列化（snake_case）")
    void agentStateResponse_field_alias() throws Exception {
        String json = """
                {
                    "agent_name": "retriever",
                    "status": "completed",
                    "progress": 1.0,
                    "intermediate_result": "Found 10 papers",
                    "duration_ms": 1200
                }
                """;

        AgentStateResponse state = objectMapper.readValue(json, AgentStateResponse.class);

        assertThat(state.getAgentName()).isEqualTo("retriever");
        assertThat(state.getStatus()).isEqualTo("completed");
        assertThat(state.getProgress()).isEqualTo(1.0);
        assertThat(state.getIntermediateResult()).isEqualTo("Found 10 papers");
        assertThat(state.getDurationMs()).isEqualTo(1200L);
    }

    @Test
    @DisplayName("UserProfileDTO - 无参构造时各字段为 null（Python 端会取默认）")
    void userProfileDTO_defaults() {
        UserProfileDTO profile = new UserProfileDTO();
        assertThat(profile.getEducationLevel()).isNull();
        assertThat(profile.getResearchField()).isNull();
        assertThat(profile.getKnowledgeLevel()).isNull();
        assertThat(profile.getPreferredStyle()).isNull();
    }

    @Test
    @DisplayName("AgentRequest - topic=\"\" 触发 @NotBlank 校验失败")
    void agentRequest_validation_blank_topic() {
        AgentRequest request = AgentRequest.builder()
                .topic("")
                .userId("usr_001")
                .build();

        Set<ConstraintViolation<AgentRequest>> violations = validator.validate(request);
        assertThat(violations).isNotEmpty();
        assertThat(violations).anyMatch(v -> v.getPropertyPath().toString().equals("topic"));
    }
}
