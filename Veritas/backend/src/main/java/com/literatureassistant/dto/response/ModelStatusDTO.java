package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

/**
 * AI 模型状态 DTO，对齐 Python 端 {@code ModelStatusResponse} Pydantic Schema（12 字段）。
 * <p>Python 端 model_dump(by_alias=True) 输出 camelCase, 用 {@link JsonProperty} 覆盖全局 SNAKE_CASE。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ModelStatusDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** LLM 服务状态 */
    private String llm;

    /** Embedding 服务状态 */
    private String embedding;

    /** ChromaDB 连接状态 */
    private String chroma;

    /** Prompt 模板加载状态 */
    private String prompts;

    /** Embedding 向量维度 */
    @JsonProperty("embeddingDimension")
    private Integer embeddingDimension;

    /** 当前活跃 LLM Provider（builtin / api / local） */
    @JsonProperty("activeLlmProvider")
    private String activeLlmProvider;

    /** 所有已加载的 LLM provider mode 列表 */
    @JsonProperty("providerCandidates")
    private List<String> providerCandidates;

    /** ChromaDB papers collection 中的论文数量 */
    @JsonProperty("chromaPaperCount")
    private Integer chromaPaperCount;

    /** GPU 显存使用（仅当本地模型加载时） */
    @JsonProperty("gpuMemoryUsed")
    private String gpuMemoryUsed;

    /** 已加载的 LLM provider 数量 */
    @JsonProperty("llmProviderCount")
    private Integer llmProviderCount;

    /** SearchService 状态: ready / not_initialized */
    @JsonProperty("searchService")
    private String searchService;

    /** Reranker 状态: ready / not_initialized */
    private String reranker;
}
