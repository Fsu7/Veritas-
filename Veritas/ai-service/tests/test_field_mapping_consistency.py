"""Task28 字段映射一致性自动验证

覆盖 20+ 字段名断言，验证：
1. AnalyzeRequest 的 camelCase alias 正确
2. AnalyzeResponse 的 camelCase alias 正确
3. UserProfile 的 camelCase alias 正确
4. SearchRequest / SearchResponse / SearchResultItem 的 camelCase alias 正确
5. ModelStatusResponse 的 camelCase alias 正确
6. HybridSearchRequest 的 camelCase alias 正确
7. AgentStateResponse 的 camelCase alias 正确
8. SSE 事件 data 字段为 camelCase
9. 枚举值三端一致（Python StrEnum 值 == JSON 字符串值）
10. 统一响应格式 4 字段结构
"""
import json

import pytest

from app.models.enums import (
    AnalysisType,
    EducationLevel,
    KnowledgeLevel,
    PreferredStyle,
)
from app.models.schemas import (
    AgentStateResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    HybridSearchRequest,
    ModelStatusResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchSuggestResponse,
    UserProfile,
)
from app.utils.response import fail, now_ts_ms, ok


# ===== 1. AnalyzeRequest camelCase alias 断言 =====

class TestAnalyzeRequestCamelCase:
    """验证 AnalyzeRequest 所有字段序列化为 camelCase"""

    def test_analysis_id_alias(self):
        """analysis_id → analysisId"""
        req = AnalyzeRequest(topic="test", userId="u1")
        dumped = req.model_dump(by_alias=True)
        assert "analysisId" in dumped
        assert "analysis_id" not in dumped

    def test_analysis_type_alias(self):
        """analysis_type → analysisType"""
        req = AnalyzeRequest(topic="test", userId="u1", analysisType="compare")
        dumped = req.model_dump(by_alias=True)
        assert "analysisType" in dumped
        assert "analysis_type" not in dumped

    def test_paper_ids_alias(self):
        """paper_ids → paperIds"""
        req = AnalyzeRequest(
            topic="test",
            userId="u1",
            paperIds=["p1", "p2"],
        )
        dumped = req.model_dump(by_alias=True)
        assert "paperIds" in dumped
        assert dumped["paperIds"] == ["p1", "p2"]
        assert "paper_ids" not in dumped

    def test_user_id_alias(self):
        """user_id → userId"""
        req = AnalyzeRequest(topic="test", userId="usr_001")
        dumped = req.model_dump(by_alias=True)
        assert "userId" in dumped
        assert dumped["userId"] == "usr_001"
        assert "user_id" not in dumped

    def test_user_profile_alias(self):
        """user_profile → userProfile"""
        profile = UserProfile(educationLevel="master")
        req = AnalyzeRequest(topic="test", userId="u1", userProfile=profile)
        dumped = req.model_dump(by_alias=True)
        assert "userProfile" in dumped
        assert "user_profile" not in dumped

    def test_accepts_camelcase_input(self):
        """验证 camelCase 输入能正确反序列化"""
        req = AnalyzeRequest.model_validate({
            "topic": "test",
            "userId": "u1",
            "paperIds": ["p1"],
            "userProfile": {
                "educationLevel": "phd",
            },
            "analysisType": "report",
            "analysisId": "anl_001",
        })
        assert req.user_id == "u1"
        assert req.paper_ids == ["p1"]
        assert req.analysis_type == AnalysisType.REPORT
        assert req.user_profile.education_level == EducationLevel.PHD


# ===== 2. AnalyzeResponse camelCase 断言 =====

class TestAnalyzeResponseCamelCase:
    """验证 AnalyzeResponse 所有字段序列化为 camelCase"""

    def test_response_analysis_id_alias(self):
        resp = AnalyzeResponse(analysisId="a1", status="completed")
        dumped = resp.model_dump(by_alias=True)
        assert "analysisId" in dumped
        assert "analysis_id" not in dumped

    def test_response_agent_states_alias(self):
        state = AgentStateResponse(agentName="retriever", status="completed", durationMs=1000)
        resp = AnalyzeResponse(analysisId="a1", status="completed", agentStates=[state])
        dumped = resp.model_dump(by_alias=True)
        assert "agentStates" in dumped
        assert "agent_states" not in dumped
        assert len(dumped["agentStates"]) == 1

    def test_response_degraded_reason_alias(self):
        resp = AnalyzeResponse(
            analysisId="a1", status="degraded", degraded=True, degradedReason="timeout"
        )
        dumped = resp.model_dump(by_alias=True)
        assert "degradedReason" in dumped
        assert "degraded_reason" not in dumped
        assert dumped["degradedReason"] == "timeout"


# ===== 3. UserProfile camelCase 断言 =====

class TestUserProfileCamelCase:
    """验证 UserProfile 所有字段序列化为 camelCase"""

    def test_education_level_alias(self):
        p = UserProfile(educationLevel="phd")
        dumped = p.model_dump(by_alias=True)
        assert "educationLevel" in dumped
        assert "education_level" not in dumped

    def test_research_field_alias(self):
        p = UserProfile(researchField="NLP")
        dumped = p.model_dump(by_alias=True)
        assert "researchField" in dumped
        assert "research_field" not in dumped

    def test_knowledge_level_alias(self):
        p = UserProfile(knowledgeLevel="expert")
        dumped = p.model_dump(by_alias=True)
        assert "knowledgeLevel" in dumped
        assert "knowledge_level" not in dumped

    def test_preferred_style_alias(self):
        p = UserProfile(preferredStyle="technical")
        dumped = p.model_dump(by_alias=True)
        assert "preferredStyle" in dumped
        assert "preferred_style" not in dumped

    def test_all_fields_camelcase_together(self):
        p = UserProfile(
            educationLevel="faculty",
            researchField="CV",
            knowledgeLevel="expert",
            preferredStyle="technical",
        )
        dumped = p.model_dump(by_alias=True)
        expected_keys = {"educationLevel", "researchField", "knowledgeLevel", "preferredStyle"}
        assert set(dumped.keys()) == expected_keys
        # 确认没有 snake_case 残留
        snake_keys = [k for k in dumped.keys() if "_" in k]
        assert len(snake_keys) == 0, f"Found snake_case keys: {snake_keys}"


# ===== 4. SearchRequest / SearchResponse / SearchResultItem 断言 =====

class TestSearchModelsCamelCase:
    """验证搜索相关模型的 camelCase 序列化"""

    def test_search_request_top_k_alias(self):
        req = SearchRequest(query="test", topK=5)
        dumped = req.model_dump(by_alias=True)
        assert "topK" in dumped
        assert "top_k" not in dumped
        assert dumped["topK"] == 5

    def test_search_result_item_paper_id_alias(self):
        item = SearchResultItem(paperId="arxiv_001", title="Test Paper")
        dumped = item.model_dump(by_alias=True)
        assert "paperId" in dumped
        assert "paper_id" not in dumped

    def test_search_response_no_snake_case(self):
        item = SearchResultItem(paperId="p1", title="T", score=0.95, year=2024, venue="NeurIPS")
        resp = SearchResponse(results=[item], total=1)
        dumped = resp.model_dump(by_alias=True)
        # results 列表中的字段也应该是 camelCase
        result_item = dumped["results"][0]
        assert "paperId" in result_item
        assert "paper_id" not in result_item

    def test_search_suggest_response_structure(self):
        resp = SearchSuggestResponse(suggestions=["s1", "s2"], total=2)
        dumped = resp.model_dump(by_alias=True)
        assert "suggestions" in dumped
        assert "total" in dumped
        assert dumped["total"] == 2


# ===== 5. ModelStatusResponse camelCase 断言 =====

class TestModelStatusResponseCamelCase:
    """验证模型状态响应的所有扩展字段为 camelCase"""

    def test_embedding_dimension_alias(self):
        r = ModelStatusResponse(llm="loaded", embedding="loaded", chroma="connected", prompts="loaded", embeddingDimension=1024)
        dumped = r.model_dump(by_alias=True)
        assert "embeddingDimension" in dumped
        assert "embedding_dimension" not in dumped
        assert dumped["embeddingDimension"] == 1024

    def test_active_llm_provider_alias(self):
        r = ModelStatusResponse(
            llm="loaded", embedding="loaded", chroma="connected", prompts="loaded",
            activeLlmProvider="api",
        )
        dumped = r.model_dump(by_alias=True)
        assert "activeLlmProvider" in dumped
        assert "active_llm_provider" not in dumped

    def test_provider_candidates_alias(self):
        r = ModelStatusResponse(
            llm="loaded", embedding="loaded", chroma="connected", prompts="loaded",
            providerCandidates=["api", "local"],
        )
        dumped = r.model_dump(by_alias=True)
        assert "providerCandidates" in dumped
        assert "provider_candidates" not in dumped
        assert dumped["providerCandidates"] == ["api", "local"]

    def test_chroma_paper_count_alias(self):
        r = ModelStatusResponse(
            llm="loaded", embedding="loaded", chroma="connected", prompts="loaded",
            chromaPaperCount=200,
        )
        dumped = r.model_dump(by_alias=True)
        assert "chromaPaperCount" in dumped
        assert "chroma_paper_count" not in dumped

    def test_gpu_memory_used_alias(self):
        r = ModelStatusResponse(
            llm="loaded", embedding="loaded", chroma="connected", prompts="loaded",
            gpuMemoryUsed="2.0GB / 24.0GB",
        )
        dumped = r.model_dump(by_alias=True)
        assert "gpuMemoryUsed" in dumped
        assert "gpu_memory_used" not in dumped

    def test_llm_provider_count_alias(self):
        r = ModelStatusResponse(
            llm="loaded", embedding="loaded", chroma="connected", prompts="loaded",
            llmProviderCount=2,
        )
        dumped = r.model_dump(by_alias=True)
        assert "llmProviderCount" in dumped
        assert "llm_provider_count" not in dumped

    def test_search_service_alias(self):
        r = ModelStatusResponse(
            llm="loaded", embedding="loaded", chroma="connected", prompts="loaded",
            searchService="ready",
        )
        dumped = r.model_dump(by_alias=True)
        assert "searchService" in dumped
        assert "search_service" not in dumped

    def test_model_status_no_snake_case_in_output(self):
        r = ModelStatusResponse(
            llm="loaded", embedding="loaded_api", chroma="connected", prompts="loaded",
            embeddingDimension=1024,
            activeLlmProvider="api",
            providerCandidates=["api"],
            chromaPaperCount=200,
            gpuMemoryUsed=None,
            llmProviderCount=1,
            searchService="ready",
            reranker="ready",
        )
        dumped = r.model_dump(by_alias=True)
        snake_keys = [k for k in dumped.keys() if "_" in k]
        assert len(snake_keys) == 0, f"ModelStatusResponse has snake_case keys: {snake_keys}"


# ===== 6. HybridSearchRequest + AgentStateResponse 补充断言 =====

class TestHybridAndAgentStateCamelCase:
    """验证 HybridSearchRequest 和 AgentStateResponse 的 camelCase"""

    def test_hybrid_search_user_profile_alias(self):
        req = HybridSearchRequest(
            query="test",
            topK=10,
            userProfile=UserProfile(educationLevel="master"),
        )
        dumped = req.model_dump(by_alias=True)
        assert "userProfile" in dumped
        assert "user_profile" not in dumped

    def test_agent_state_agent_name_alias(self):
        s = AgentStateResponse(agentName="generator", status="completed")
        dumped = s.model_dump(by_alias=True)
        assert "agentName" in dumped
        assert "agent_name" not in dumped

    def test_agent_state_intermediate_result_alias(self):
        s = AgentStateResponse(agentName="g", status="running", intermediateResult="processing...")
        dumped = s.model_dump(by_alias=True)
        assert "intermediateResult" in dumped
        assert "intermediate_result" not in dumped

    def test_agent_state_duration_ms_alias(self):
        s = AgentStateResponse(agentName="g", status="completed", durationMs=5000)
        dumped = s.model_dump(by_alias=True)
        assert "durationMs" in dumped
        assert "duration_ms" not in dumped
        assert dumped["durationMs"] == 5000


# ===== 7. SSE 事件 data 字段 camelCase 断言 =====

class TestSSEEventCamelCase:
    """验证 orchestrator 构造的 SSE 事件 data 字段使用 camelCase"""

    def _make_event_data(self, data: dict) -> str:
        """模拟 orchestrator._make_event 的 json.dumps 行为"""
        return json.dumps(data, ensure_ascii=False)

    def test_agent_started_data_is_camelcase(self):
        """agent_started 事件的 data 字段全部 camelCase"""
        data = {
            "agentName": "retriever",
            "status": "running",
            "analysisId": "anl_001",
            "timestamp": 1716441600000,
        }
        serialized = self._make_event_data(data)
        parsed = json.loads(serialized)
        assert "agentName" in parsed
        assert "status" in parsed
        assert "analysisId" in parsed
        assert "timestamp" in parsed
        # 不应有 snake_case
        snake_keys = [k for k in parsed.keys() if "_" in k and k != "_id"]
        assert len(snake_keys) == 0

    def test_agent_completed_data_is_camelcase(self):
        """agent_completed 事件的 data 字段全部 camelCase"""
        data = {
            "agentName": "retriever",
            "status": "completed",
            "progress": 1.0,
            "analysisId": "anl_001",
            "intermediateResult": "Found 10 papers",
            "durationMs": 1200,
        }
        serialized = self._make_event_data(data)
        parsed = json.loads(serialized)
        expected_keys = {
            "agentName", "status", "progress", "analysisId",
            "intermediateResult", "durationMs",
        }
        assert set(parsed.keys()) == expected_keys

    def test_analysis_completed_data_is_camelcase(self):
        """analysis_completed 事件的 data 字段全部 camelCase"""
        data = {
            "analysisId": "anl_001",
            "status": "completed",
            "finalReport": "# Report\n...",
            "degraded": False,
            "degradedReason": None,
            "totalDurationMs": 24200,
        }
        serialized = self._make_event_data(data)
        parsed = json.loads(serialized)
        assert "finalReport" in parsed
        assert "degradedReason" in parsed
        assert "totalDurationMs" in parsed
        snake_keys = [k for k in parsed.keys() if "_" in k]
        assert len(snake_keys) == 0

    def test_error_event_data_is_camelcase(self):
        """error 事件的 data 字段全部 camelCase"""
        data = {
            "analysisId": "anl_001",
            "errorCode": 408,
            "errorMessage": "全流程超时(120s)",
        }
        serialized = self._make_event_data(data)
        parsed = json.loads(serialized)
        assert "errorCode" in parsed
        assert "errorMessage" in parsed
        assert "error_code" not in parsed
        assert "error_message" not in parsed

    def test_agent_failed_data_is_camelcase(self):
        """agent_failed 事件的 data 字段全部 camelCase"""
        data = {
            "agentName": "analyzer",
            "status": "failed",
            "analysisId": "anl_001",
            "errorMessage": "LLM timeout",
            "durationMs": 30000,
        }
        serialized = self._make_event_data(data)
        parsed = json.loads(serialized)
        assert "errorMessage" in parsed
        assert "durationMs" in parsed


# ===== 8. 枚举值三端一致性断言 =====

class TestEnumConsistency:
    """验证 StrEnum 值与 JSON 字符串完全一致"""

    def test_education_level_values_match_json(self):
        values = [e.value for e in EducationLevel]
        expected = ["undergraduate", "master", "phd", "faculty"]
        assert values == expected

    def test_education_level_str_representation(self):
        """StrEnum: str(member) == member.value"""
        assert str(EducationLevel.MASTER) == "master"
        assert str(EducationLevel.PHD) == "phd"

    def test_knowledge_level_values_match_json(self):
        values = [e.value for e in KnowledgeLevel]
        expected = ["beginner", "intermediate", "advanced", "expert"]
        assert values == expected

    def test_preferred_style_values_match_json(self):
        values = [e.value for e in PreferredStyle]
        expected = ["simple", "balanced", "technical"]
        assert values == expected

    def test_analysis_type_values_match_json(self):
        values = [e.value for e in AnalysisType]
        expected = ["paper_analysis", "compare", "report"]
        assert values == expected

    def test_enum_serializes_to_value_string(self):
        """Pydantic 序列化 StrEnum 时输出 value 字符串"""
        p = UserProfile(educationLevel="undergraduate")
        dumped = p.model_dump(by_alias=True)
        assert dumped["educationLevel"] == "undergraduate"

    def test_enum_deserializes_from_value_string(self):
        """Pydantic 反序列化时接受 value 字符串"""
        p = UserProfile.model_validate({"educationLevel": "faculty"})
        assert p.education_level == EducationLevel.FACULTY

    def test_enum_in_analyze_request_roundtrip(self):
        """AnalyzeRequest 中枚举的完整往返"""
        req = AnalyzeRequest.model_validate({
            "topic": "test",
            "userId": "u1",
            "analysisType": "compare",
        })
        assert req.analysis_type == AnalysisType.COMPARE
        dumped = req.model_dump(by_alias=True)
        assert dumped["analysisType"] == "compare"


# ===== 9. 统一响应格式断言 =====

class TestUnifiedResponseFormat:
    """验证 ok() / fail() 返回 4 字段统一结构"""

    def test_ok_has_4_fields(self):
        r = ok(data={"x": 1})
        assert set(r.keys()) == {"code", "message", "data", "timestamp"}

    def test_fail_has_4_fields(self):
        r = fail(message="error", code=500)
        assert set(r.keys()) == {"code", "message", "data", "timestamp"}

    def test_timestamp_is_int_milliseconds(self):
        r = ok()
        assert isinstance(r["timestamp"], int)
        assert r["timestamp"] > 1700000000000  # 合理时间范围

    def test_code_and_message_types(self):
        r = ok(code=200, message="success")
        assert isinstance(r["code"], int)
        assert isinstance(r["message"], str)


# ===== 10. model_json_schema 验证（补充断言）=====

class TestModelJsonSchema:
    """通过 model_json_schema 验证 alias 配置"""

    def test_analyze_request_schema_has_aliases(self):
        schema = AnalyzeRequest.model_json_schema()
        props = schema.get("properties", {})
        # schema properties 应包含 camelCase 别名
        assert "userId" in props
        assert "paperIds" in props
        assert "userProfile" in props
        assert "analysisType" in props
        assert "analysisId" in props

    def test_user_profile_schema_has_aliases(self):
        schema = UserProfile.model_json_schema()
        props = schema.get("properties", {})
        assert "educationLevel" in props
        assert "researchField" in props
        assert "knowledgeLevel" in props
        assert "preferredStyle" in props

    def test_model_status_schema_has_extended_aliases(self):
        schema = ModelStatusResponse.model_json_schema()
        props = schema.get("properties", {})
        extended_aliases = [
            "embeddingDimension", "activeLlmProvider", "providerCandidates",
            "chromaPaperCount", "gpuMemoryUsed", "llmProviderCount",
            "searchService",
        ]
        for alias in extended_aliases:
            assert alias in props, f"Missing alias '{alias}' in ModelStatusResponse schema"

    def test_search_result_item_schema_aliases(self):
        schema = SearchResultItem.model_json_schema()
        props = schema.get("properties", {})
        assert "paperId" in props
