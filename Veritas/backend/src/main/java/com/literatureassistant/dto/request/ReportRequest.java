package com.literatureassistant.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 综述生成请求 DTO（task26 新建）。
 * <p>基于多篇论文生成个性化综述报告，编排逻辑与 analyzePaper 类似但 AnalysisType.REPORT。
 * <p>论文数量上限 20 篇，防止滥用（大量 paperIds 导致 AI 调用超时/Token爆炸）。
 * <p>字段命名：使用 Java camelCase（依赖全局 Jackson SNAKE_CASE 转换到 Python/JSON）。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReportRequest {

    /** 研究主题，必填，最大 500 字符 */
    @NotBlank(message = "研究主题不能为空")
    @Size(max = 500, message = "研究主题长度不能超过500")
    private String topic;

    /** 论文 ID 列表，必填，1-20 个 */
    @NotEmpty(message = "论文ID列表不能为空")
    @Size(max = 20, message = "论文数量不能超过20")
    private List<String> paperIds;

    /** 可选；为空时新建 Session */
    private String sessionId;
}
