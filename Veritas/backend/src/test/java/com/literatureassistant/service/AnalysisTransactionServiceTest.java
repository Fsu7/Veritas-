package com.literatureassistant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.AnalysisTaskResponse;
import com.literatureassistant.entity.AnalysisResult;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.repository.AnalysisResultRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * AnalysisTransactionService 单元测试（task24 重构产物）。
 * <p>覆盖 savePending / completeAnalysis 两个事务方法的行为，验证重构后事务方法职责完整迁移。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@ExtendWith(MockitoExtension.class)
class AnalysisTransactionServiceTest {

    @Mock
    private AnalysisResultRepository analysisResultRepository;

    private AnalysisTransactionService service;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() {
        service = new AnalysisTransactionService(analysisResultRepository, objectMapper);
    }

    @Test
    @DisplayName("savePending - 创建 PENDING 状态 AnalysisResult + result='{}'")
    void savePending_creates_pending_analysis_result() {
        when(analysisResultRepository.save(any(AnalysisResult.class)))
                .thenAnswer(inv -> {
                    AnalysisResult arg = inv.getArgument(0);
                    arg.setId(100L);
                    return arg;
                });

        AnalysisResult saved = service.savePending("anl_001", "ses_001", AnalysisType.PAPER_ANALYSIS);

        assertThat(saved).isNotNull();
        assertThat(saved.getAnalysisId()).isEqualTo("anl_001");
        assertThat(saved.getSessionId()).isEqualTo("ses_001");
        assertThat(saved.getType()).isEqualTo(AnalysisType.PAPER_ANALYSIS);
        assertThat(saved.getStatus()).isEqualTo(AnalysisStatus.PENDING);
        assertThat(saved.getResult()).isEqualTo("{}");

        ArgumentCaptor<AnalysisResult> captor = ArgumentCaptor.forClass(AnalysisResult.class);
        verify(analysisResultRepository).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(AnalysisStatus.PENDING);
    }

    @Test
    @DisplayName("savePending - 返回 Repository.save 的返回值")
    void savePending_returns_saved_entity() {
        AnalysisResult stub = AnalysisResult.builder()
                .id(200L)
                .analysisId("anl_002")
                .sessionId("ses_002")
                .type(AnalysisType.COMPARE)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .build();
        when(analysisResultRepository.save(any(AnalysisResult.class))).thenReturn(stub);

        AnalysisResult returned = service.savePending("anl_002", "ses_002", AnalysisType.COMPARE);

        assertThat(returned).isSameAs(stub);
        assertThat(returned.getId()).isEqualTo(200L);
    }

    @Test
    @DisplayName("completeAnalysis - 更新 status + result JSON + 返回 AnalysisTaskResponse")
    void completeAnalysis_updates_status_and_result() {
        AnalysisResult entity = AnalysisResult.builder()
                .id(1L)
                .analysisId("anl_001")
                .sessionId("ses_001")
                .type(AnalysisType.PAPER_ANALYSIS)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .createdAt(LocalDateTime.of(2026, 6, 1, 10, 0))
                .build();
        when(analysisResultRepository.findById(1L)).thenReturn(Optional.of(entity));
        when(analysisResultRepository.save(any(AnalysisResult.class))).thenReturn(entity);

        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_001")
                .status(AnalysisStatus.COMPLETED)
                .report("## Report")
                .degraded(false)
                .build();

        AnalysisTaskResponse response = service.completeAnalysis(1L, result);

        assertThat(response).isNotNull();
        assertThat(response.getAnalysisId()).isEqualTo("anl_001");
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(response.getMessage()).isEqualTo("分析完成");
        assertThat(entity.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(entity.getResult()).contains("## Report");
    }

    @Test
    @DisplayName("completeAnalysis - degraded=true → status=COMPLETED（非 FAILED）")
    void completeAnalysis_degraded_result_sets_COMPLETED() {
        AnalysisResult entity = AnalysisResult.builder()
                .id(2L)
                .analysisId("anl_002")
                .sessionId("ses_002")
                .type(AnalysisType.REPORT)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .createdAt(LocalDateTime.now())
                .build();
        when(analysisResultRepository.findById(2L)).thenReturn(Optional.of(entity));
        when(analysisResultRepository.save(any(AnalysisResult.class))).thenReturn(entity);

        AnalysisResultDTO degraded = AnalysisResultDTO.builder()
                .analysisId("anl_002")
                .degraded(true)
                .degradedReason("AI服务暂时不可用")
                .build();

        AnalysisTaskResponse response = service.completeAnalysis(2L, degraded);

        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(response.getMessage()).contains("降级").contains("AI服务暂时不可用");
        assertThat(entity.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
    }

    @Test
    @DisplayName("completeAnalysis - entity 不存在 → 抛 ResourceNotFoundException(404)")
    void completeAnalysis_entity_not_found_throws_404() {
        when(analysisResultRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.completeAnalysis(99L, AnalysisResultDTO.builder().build()))
                .isInstanceOf(ResourceNotFoundException.class);
        verify(analysisResultRepository, never()).save(any(AnalysisResult.class));
    }

    @Test
    @DisplayName("completeAnalysis - result=null → status=FAILED + message 含'失败'")
    void completeAnalysis_null_result_sets_FAILED() {
        AnalysisResult entity = AnalysisResult.builder()
                .id(3L)
                .analysisId("anl_003")
                .sessionId("ses_003")
                .type(AnalysisType.PAPER_ANALYSIS)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .createdAt(LocalDateTime.now())
                .build();
        when(analysisResultRepository.findById(3L)).thenReturn(Optional.of(entity));
        when(analysisResultRepository.save(any(AnalysisResult.class))).thenReturn(entity);

        AnalysisTaskResponse response = service.completeAnalysis(3L, null);

        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.FAILED);
        assertThat(response.getMessage()).contains("失败");
    }
}
