package com.literatureassistant.controller;

import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.request.SessionCreateRequest;
import com.literatureassistant.dto.request.SessionStatusUpdateRequest;
import com.literatureassistant.dto.response.SessionDetailResponse;
import com.literatureassistant.dto.response.SessionResponse;
import com.literatureassistant.enums.SessionStatus;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.GlobalExceptionHandler;
import com.literatureassistant.service.SessionService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;

import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@ExtendWith(MockitoExtension.class)
class SessionControllerTest {

    @InjectMocks
    private SessionController sessionController;

    @Mock
    private SessionService sessionService;

    private MockMvc mockMvc;

    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper()
                .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                .enable(MapperFeature.ACCEPT_CASE_INSENSITIVE_ENUMS)
                .registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        MappingJackson2HttpMessageConverter converter = new MappingJackson2HttpMessageConverter(objectMapper);
        mockMvc = MockMvcBuilders.standaloneSetup(sessionController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .setValidator(new LocalValidatorFactoryBean())
                .setMessageConverters(converter)
                .build();
    }

    @Test
    @DisplayName("POST /api/sessions - 正常创建返回201和SessionResponse")
    void createSession_success() throws Exception {
        SessionResponse response = SessionResponse.builder()
                .sessionId("ses_001")
                .userId("usr_001")
                .topic("Multi-Agent协同决策")
                .status("ACTIVE")
                .createdAt(LocalDateTime.now())
                .build();

        when(sessionService.createSession(any(), any(SessionCreateRequest.class)))
                .thenReturn(response);

        SessionCreateRequest request = SessionCreateRequest.builder()
                .topic("Multi-Agent协同决策")
                .build();

        mockMvc.perform(post("/api/sessions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.session_id").value("ses_001"))
                .andExpect(jsonPath("$.data.user_id").value("usr_001"))
                .andExpect(jsonPath("$.data.topic").value("Multi-Agent协同决策"))
                .andExpect(jsonPath("$.data.status").value("ACTIVE"));
    }

    @Test
    @DisplayName("GET /api/sessions - 正常列表返回200和PageResponse")
    void listSessions_success() throws Exception {
        SessionResponse s1 = SessionResponse.builder()
                .sessionId("ses_001")
                .userId("usr_001")
                .topic("Topic A")
                .status("ACTIVE")
                .createdAt(LocalDateTime.now())
                .build();
        PageResponse<SessionResponse> page = PageResponse.<SessionResponse>builder()
                .items(List.of(s1))
                .page(1)
                .size(10)
                .total(1L)
                .totalPages(1)
                .build();

        when(sessionService.listSessions(any(), anyInt(), anyInt())).thenReturn(page);

        mockMvc.perform(get("/api/sessions?page=1&size=10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.items[0].session_id").value("ses_001"))
                .andExpect(jsonPath("$.data.items[0].user_id").value("usr_001"))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.total_pages").value(1));
    }

    @Test
    @DisplayName("GET /api/sessions/{sessionId} - 正常查询返回200和SessionDetailResponse")
    void getSessionDetail_success() throws Exception {
        SessionDetailResponse detail = SessionDetailResponse.builder()
                .sessionId("ses_001")
                .userId("usr_001")
                .topic("Topic A")
                .status("ACTIVE")
                .createdAt(LocalDateTime.now())
                .analysisCount(3)
                .build();

        when(sessionService.getSessionDetail("ses_001")).thenReturn(detail);

        mockMvc.perform(get("/api/sessions/ses_001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.session_id").value("ses_001"))
                .andExpect(jsonPath("$.data.analysis_count").value(3));
    }

    @Test
    @DisplayName("PUT /api/sessions/{sessionId}/status - 正常更新返回200")
    void updateStatus_success() throws Exception {
        SessionStatusUpdateRequest req = SessionStatusUpdateRequest.builder()
                .status(SessionStatus.COMPLETED)
                .build();
        doNothing().when(sessionService).updateStatus(eq("ses_001"), eq(SessionStatus.COMPLETED));

        mockMvc.perform(put("/api/sessions/ses_001/status")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("PUT /api/sessions/{sessionId}/status - lowercase 枚举可被反序列化")
    void updateStatus_acceptCaseInsensitiveEnum() throws Exception {
        doNothing().when(sessionService).updateStatus(eq("ses_001"), eq(SessionStatus.COMPLETED));

        mockMvc.perform(put("/api/sessions/ses_001/status")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"completed\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("DELETE /api/sessions/{sessionId} - 正常删除返回200")
    void deleteSession_success() throws Exception {
        doNothing().when(sessionService).deleteSession("ses_001");

        mockMvc.perform(delete("/api/sessions/ses_001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("数据隔离: 用户B查询用户A的会话详情, Service抛403 -> Controller返回403")
    void getSessionDetail_isolation_userBAccessUserA_returns403() throws Exception {
        when(sessionService.getSessionDetail("ses_userA"))
                .thenThrow(new BusinessException(403, "无权访问该会话", "FORBIDDEN"));

        mockMvc.perform(get("/api/sessions/ses_userA"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
    }

    @Test
    @DisplayName("数据隔离: 用户B删除用户A的会话, Service抛403 -> Controller返回403")
    void deleteSession_isolation_userBDeleteUserA_returns403() throws Exception {
        doThrow(new BusinessException(403, "无权删除该会话", "FORBIDDEN"))
                .when(sessionService).deleteSession("ses_userA");

        mockMvc.perform(delete("/api/sessions/ses_userA"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
    }

    @Test
    @DisplayName("数据隔离: 用户B更新用户A的会话状态, Service抛403 -> Controller返回403")
    void updateStatus_isolation_userBUpdateUserA_returns403() throws Exception {
        SessionStatusUpdateRequest req = SessionStatusUpdateRequest.builder()
                .status(SessionStatus.COMPLETED)
                .build();
        doThrow(new BusinessException(403, "无权修改该会话", "FORBIDDEN"))
                .when(sessionService).updateStatus(eq("ses_userA"), eq(SessionStatus.COMPLETED));

        mockMvc.perform(put("/api/sessions/ses_userA/status")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(req)))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
    }
}
