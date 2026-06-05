package com.literatureassistant.dto.common;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.literatureassistant.enums.AnalysisType;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

/**
 * Java → Python AnalyzeRequest 请求体。
 * <p>对齐 Python 端 {@code AnalyzeRequest} Pydantic Schema。
 * <p>Python 端 by_alias="camelCase" + populate_by_name=True, 用 {@link JsonProperty} 显式输出 camelCase
 * 避免全局 SNAKE_CASE 影响。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AgentRequest implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 研究主题，必填，1-500 字符
     */
    @NotBlank(message = "研究主题不能为空")
    @Size(max = 500, message = "研究主题长度不能超过500")
    private String topic;

    /**
     * 论文 ID 列表，可空
     */
    @JsonProperty("paperIds")
    private List<String> paperIds;

    /**
     * 用户 ID，必填
     */
    @NotBlank(message = "用户ID不能为空")
    @JsonProperty("userId")
    private String userId;

    /**
     * 用户画像，可空（缺失时 Python 端取默认 master/intermediate/balanced）
     */
    @Valid
    @JsonProperty("userProfile")
    private UserProfileDTO userProfile;

    /**
     * 分析类型枚举，默认 {@code REPORT}
     */
    @JsonProperty("analysisType")
    private AnalysisType analysisType;

    /**
     * 分析任务 ID（Java 端生成），可空
     */
    @JsonProperty("analysisId")
    private String analysisId;
}
