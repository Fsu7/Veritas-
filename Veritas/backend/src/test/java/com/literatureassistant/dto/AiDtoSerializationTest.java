package com.literatureassistant.dto;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.common.UserProfileDTO;
import com.literatureassistant.dto.response.AgentSseEvent;
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
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * AI DTO 序列化/反序列化/校验 单元测试。
 * <p>覆盖 8 个核心场景：AgentRequest 序列化/反序列化、AnalysisResultDTO 枚举映射、
 * AgentStateResponse 字段映射、UserProfileDTO 默认值、AgentRequest 校验、
 * ModelStatusDTO 字段映射、PaperSearchResultDTO 字段映射、AgentSseEvent 字段映射。
 * <p>Python 端 by_alias=True 输出 camelCase, Java 端全局 SNAKE_CASE 由 @JsonProperty 显式覆盖。
 */
class AiDtoSerializationTest {

    private static ObjectMapper objectMapper;
    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void setUp() {
        // 模拟 application.yml: 全局 SNAKE_CASE + JavaTimeModule + 大小写不敏感枚举
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
    @DisplayName("AgentRequest - 序列化为 camelCase JSON（@JsonProperty 覆盖全局 SNAKE_CASE）")
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

        // @JsonProperty 标注字段, 全局 SNAKE_CASE 不会生效, 输出 camelCase
        assertThat(json).contains("\"paperIds\":[\"arxiv_2024_001\"]");
        assertThat(json).contains("\"userId\":\"usr_001\"");
        assertThat(json).contains("\"userProfile\":");
        assertThat(json).contains("\"educationLevel\":\"master\"");
        assertThat(json).contains("\"researchField\":\"NLP\"");
        assertThat(json).contains("\"analysisType\":\"paper_analysis\"");
        assertThat(json).contains("\"analysisId\":\"anl_001\"");
    }

    @Test
    @DisplayName("AgentRequest - Python camelCase JSON 反序列化正确解析")
    void agentRequest_deserialization_from_python() throws Exception {
        // Python 端 model_dump(by_alias=True) 输出 camelCase
        String pythonJson = """
                {
                    "topic": "Multi-Agent协同决策",
                    "paperIds": ["arxiv_2024_001"],
                    "userId": "usr_001",
                    "userProfile": {
                        "educationLevel": "master",
                        "researchField": "NLP",
                        "knowledgeLevel": "intermediate",
                        "preferredStyle": "balanced"
                    },
                    "analysisType": "report",
                    "analysisId": "anl_002"
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
                    {"analysisId": "anl_x", "status": "%s", "degraded": false}
                    """.formatted(status.getDbValue());
            AnalysisResultDTO dto = objectMapper.readValue(json, AnalysisResultDTO.class);
            assertThat(dto.getStatus()).isEqualTo(status);
        }
    }

    @Test
    @DisplayName("AgentStateResponse - 5 字段正确反序列化（camelCase）")
    void agentStateResponse_field_alias() throws Exception {
        // Python 端 by_alias=True 输出 camelCase
        String json = """
                {
                    "agentName": "retriever",
                    "status": "completed",
                    "progress": 1.0,
                    "intermediateResult": "Found 10 papers",
                    "durationMs": 1200
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

    @Test
    @DisplayName("ModelStatusDTO - 12 字段正确反序列化（camelCase）")
    void modelStatusDTO_field_mapping() throws Exception {
        // Python 端 ModelStatusResponse by_alias=True 输出 camelCase, 包含扩展 6 字段
        String json = """
                {
                    "llm": "loaded",
                    "embedding": "loaded_api",
                    "chroma": "connected",
                    "prompts": "loaded",
                    "embeddingDimension": 1024,
                    "activeLlmProvider": "api",
                    "providerCandidates": ["api", "local"],
                    "chromaPaperCount": 200,
                    "gpuMemoryUsed": null,
                    "llmProviderCount": 2,
                    "searchService": "ready",
                    "reranker": "ready"
                }
                """;

        ModelStatusDTO dto = objectMapper.readValue(json, ModelStatusDTO.class);

        assertThat(dto.getLlm()).isEqualTo("loaded");
        assertThat(dto.getEmbedding()).isEqualTo("loaded_api");
        assertThat(dto.getEmbeddingDimension()).isEqualTo(1024);
        assertThat(dto.getActiveLlmProvider()).isEqualTo("api");
        assertThat(dto.getProviderCandidates()).containsExactly("api", "local");
        assertThat(dto.getChromaPaperCount()).isEqualTo(200);
        assertThat(dto.getLlmProviderCount()).isEqualTo(2);
        assertThat(dto.getSearchService()).isEqualTo("ready");
        assertThat(dto.getReranker()).isEqualTo("ready");
    }

    @Test
    @DisplayName("PaperSearchResultDTO - paperId/abstract 字段正确反序列化（camelCase）")
    void paperSearchResultDTO_field_mapping() throws Exception {
        // Python 端 SearchResultItem by_alias=True 输出 camelCase
        String json = """
                {
                    "paperId": "arxiv_2024_001",
                    "title": "Attention Is All You Need",
                    "abstract": "We propose a new network architecture",
                    "score": 0.95,
                    "year": 2017,
                    "venue": "NeurIPS"
                }
                """;

        PaperSearchResultDTO dto = objectMapper.readValue(json, PaperSearchResultDTO.class);

        assertThat(dto.getPaperId()).isEqualTo("arxiv_2024_001");
        assertThat(dto.getTitle()).isEqualTo("Attention Is All You Need");
        assertThat(dto.getAbstractText()).isEqualTo("We propose a new network architecture");
        assertThat(dto.getScore()).isEqualTo(0.95);
    }

    @Test
    @DisplayName("AgentSseEvent - id/event/data 字段正确反序列化（camelCase）")
    void agentSseEvent_field_mapping() throws Exception {
        String json = """
                {
                    "id": 5,
                    "event": "agent_state_update",
                    "data": {
                        "agentName": "retriever",
                        "status": "running",
                        "progress": 0.5,
                        "analysisId": "anl_001"
                    }
                }
                """;

        AgentSseEvent event = objectMapper.readValue(json, AgentSseEvent.class);

        assertThat(event.getId()).isEqualTo(5L);
        assertThat(event.getEvent()).isEqualTo("agent_state_update");
        assertThat(event.getData()).isNotNull();
        assertThat(event.getData().get("agentName")).isEqualTo("retriever");
        assertThat(event.getData().get("progress")).isEqualTo(0.5);
    }
}
