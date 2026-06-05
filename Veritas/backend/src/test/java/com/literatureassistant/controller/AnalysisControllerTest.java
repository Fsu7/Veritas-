package com.literatureassistant.controller;

import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.dto.request.PaperAnalysisRequest;
import com.literatureassistant.dto.response.AnalysisTaskResponse;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.exception.GlobalExceptionHandler;
import com.literatureassistant.service.AnalysisService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;

import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * AnalysisController MockMvc 单元测试。
 *
 * @author XH-202630 Literature Assistant
 */
@ExtendWith(MockitoExtension.class)
class AnalysisControllerTest {

    @InjectMocks
    private AnalysisController analysisController;

    @Mock
    private AnalysisService analysisService;

    private MockMvc mockMvc;
    private ObjectMapper objectMapper;
    private static final String CURRENT_USER_ID = "usr_001";

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper()
                .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                .enable(MapperFeature.ACCEPT_CASE_INSENSITIVE_ENUMS)
                .registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        MappingJackson2HttpMessageConverter converter = new MappingJackson2HttpMessageConverter(objectMapper);
        mockMvc = MockMvcBuilders.standaloneSetup(analysisController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .setValidator(new LocalValidatorFactoryBean())
                .setMessageConverters(converter)
                .build();

        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(new UsernamePasswordAuthenticationToken(CURRENT_USER_ID, null, List.of()));
        SecurityContextHolder.setContext(context);
    }

    private AnalysisTaskResponse buildResponse() {
        return AnalysisTaskResponse.builder()
                .analysisId("anl_abcdef012345")
                .status(AnalysisStatus.COMPLETED)
                .message("分析完成")
                .createdAt(LocalDateTime.of(2026, 6, 1, 10, 0, 0))
                .build();
    }

    @Test
    @DisplayName("POST /api/analysis/paper - 正常返回 202 + analysisId")
    void analyzePaperController_success_returns202() throws Exception {
        when(analysisService.analyzePaper(anyString(), any(PaperAnalysisRequest.class)))
                .thenReturn(buildResponse());

        PaperAnalysisRequest request = PaperAnalysisRequest.builder()
                .topic("Multi-Agent协同决策")
                .paperId("arxiv_2024_001")
                .build();

        mockMvc.perform(post("/api/analysis/paper")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request))
                        .principal(new UsernamePasswordAuthenticationToken(CURRENT_USER_ID, null, List.of())))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.analysis_id").value("anl_abcdef012345"))
                .andExpect(jsonPath("$.data.status").value("completed"));
    }

    @Test
    @DisplayName("POST /api/analysis/paper - topic=\"\" 返回 400 + 校验错误")
    void analyzePaperController_blank_topic_returns400() throws Exception {
        PaperAnalysisRequest request = PaperAnalysisRequest.builder()
                .topic("")
                .paperId("arxiv_2024_001")
                .build();

        mockMvc.perform(post("/api/analysis/paper")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request))
                        .principal(new UsernamePasswordAuthenticationToken(CURRENT_USER_ID, null, List.of())))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("POST /api/analysis/paper - 未认证返回 401")
    void analyzePaperController_unauthenticated_returns401() throws Exception {
        // 清空 SecurityContext
        SecurityContextHolder.clearContext();

        PaperAnalysisRequest request = PaperAnalysisRequest.builder()
                .topic("test")
                .paperId("arxiv_2024_001")
                .build();

        mockMvc.perform(post("/api/analysis/paper")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value(401));
    }

    @Test
    @DisplayName("POST /api/analysis/paper - paperId 缺失返回 400")
    void analyzePaperController_blank_paperId_returns400() throws Exception {
        PaperAnalysisRequest request = PaperAnalysisRequest.builder()
                .topic("test")
                .paperId("")
                .build();

        mockMvc.perform(post("/api/analysis/paper")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request))
                        .principal(new UsernamePasswordAuthenticationToken(CURRENT_USER_ID, null, List.of())))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("POST /api/analysis/paper - AI 降级时返回 202 + status=completed + degraded 消息")
    void analyzePaperController_aiDown_returns_degraded() throws Exception {
        AnalysisTaskResponse degradedResponse = AnalysisTaskResponse.builder()
                .analysisId("anl_aaaa")
                .status(AnalysisStatus.COMPLETED)
                .message("分析完成（降级）：AI服务暂时不可用")
                .createdAt(LocalDateTime.now())
                .build();
        when(analysisService.analyzePaper(anyString(), any(PaperAnalysisRequest.class)))
                .thenReturn(degradedResponse);

        PaperAnalysisRequest request = PaperAnalysisRequest.builder()
                .topic("test")
                .paperId("arxiv_2024_001")
                .build();

        mockMvc.perform(post("/api/analysis/paper")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request))
                        .principal(new UsernamePasswordAuthenticationToken(CURRENT_USER_ID, null, List.of())))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.data.status").value("completed"))
                .andExpect(jsonPath("$.data.message").value(org.hamcrest.Matchers.containsString("降级")));
    }
}
