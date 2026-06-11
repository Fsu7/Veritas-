package com.literatureassistant.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 对比分析请求 DTO（task25 新建）。
 * <p>2-5 篇论文的对比分析，编排逻辑与 analyzePaper 类似但 AnalysisType.COMPARE。
 * <p>字段命名：使用 Java camelCase（依赖全局 Jackson SNAKE_CASE 转换到 Python/JSON）。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompareRequest {

    /** 研究主题，必填，最大 500 字符 */
    @NotBlank(message = "研究主题不能为空")
    @Size(max = 500, message = "研究主题长度不能超过500")
    private String topic;

    /** 论文 ID 列表，必填，2-5 个 */
    @NotNull(message = "论文ID列表不能为空")
    @Size(min = 2, max = 5, message = "论文数量必须在2-5之间")
    private List<String> paperIds;

    /** 可选；为空时新建 Session */
    private String sessionId;
}
