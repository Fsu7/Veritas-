package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * AI 模型状态 DTO，对齐 Python 端 {@code ModelStatusResponse} Pydantic Schema（6 字段）。
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
    private Integer embeddingDimension;

    /** 当前活跃 LLM Provider（builtin / api / local） */
    private String activeLlmProvider;
}
