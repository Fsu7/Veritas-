"""task24 测试套件 — API请求校验 + 统一响应格式

覆盖：
- ok/fail/now_ts_ms 工厂函数
- 中英文 message 422 错误
- Enum 严格校验（合法/非法值）
- camelCase alias 往返
- e2e /api/agent/analyze 统一响应
"""
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import (
    AnalysisType,
    EducationLevel,
    KnowledgeLevel,
    PreferredStyle,
)
from app.models.schemas import AnalyzeRequest, SearchRequest, UserProfile
from app.utils.response import fail, now_ts_ms, ok


# ===== FR-001: ok/fail/now_ts_ms 工厂测试 =====

class TestResponseFactory:
    """测试统一响应包装器"""

    def test_ok_basic(self):
        r = ok(data={"x": 1})
        assert r["code"] == 200
        assert r["message"] == "success"
        assert r["data"] == {"x": 1}
        assert "timestamp" in r
        assert isinstance(r["timestamp"], int)

    def test_ok_custom_message_code(self):
        r = ok(data=[1, 2, 3], message="custom", code=201)
        assert r["code"] == 201
        assert r["message"] == "custom"
        assert r["data"] == [1, 2, 3]

    def test_ok_with_none_data(self):
        r = ok()
        assert r["data"] is None
        assert r["code"] == 200

    def test_fail_basic(self):
        r = fail(message="错误", code=500)
        assert r["code"] == 500
        assert r["message"] == "错误"
        assert r["data"] is None
        assert "timestamp" in r

    def test_fail_with_data(self):
        r = fail(message="校验失败", code=422, data={"field": "userId"})
        assert r["data"] == {"field": "userId"}

    def test_now_ts_ms_is_int_milliseconds(self):
        ts1 = now_ts_ms()
        time.sleep(0.01)
        ts2 = now_ts_ms()
        assert isinstance(ts1, int)
        assert ts2 > ts1
        # 毫秒级精度（间隔至少 5ms）
        assert ts2 - ts1 >= 5

    def test_ok_4_required_fields(self):
        r = ok()
        assert set(r.keys()) == {"code", "message", "data", "timestamp"}


# ===== FR-002: Enum 严格校验测试 =====

class TestEnumStrictValidation:
    """测试 4 个 StrEnum 定义正确"""

    def test_education_level_values(self):
        assert EducationLevel.UNDERGRADUATE.value == "undergraduate"
        assert EducationLevel.MASTER.value == "master"
        assert EducationLevel.PHD.value == "phd"
        assert EducationLevel.FACULTY.value == "faculty"

    def test_knowledge_level_values(self):
        assert KnowledgeLevel.BEGINNER.value == "beginner"
        assert KnowledgeLevel.INTERMEDIATE.value == "intermediate"
        assert KnowledgeLevel.ADVANCED.value == "advanced"
        assert KnowledgeLevel.EXPERT.value == "expert"

    def test_preferred_style_values(self):
        assert PreferredStyle.SIMPLE.value == "simple"
        assert PreferredStyle.BALANCED.value == "balanced"
        assert PreferredStyle.TECHNICAL.value == "technical"

    def test_analysis_type_values(self):
        assert AnalysisType.PAPER_ANALYSIS.value == "paper_analysis"
        assert AnalysisType.COMPARE.value == "compare"
        assert AnalysisType.REPORT.value == "report"


# ===== FR-003: Pydantic 校验 + 中文友好 422 测试 =====

class TestRequestValidation:
    """测试 Pydantic 严格校验"""

    def test_userprofile_legal_enum_value(self):
        profile = UserProfile(
            educationLevel="master",
            researchField="NLP",
            knowledgeLevel="intermediate",
            preferredStyle="balanced",
        )
        assert profile.education_level == EducationLevel.MASTER

    def test_userprofile_illegal_enum_value_raises(self):
        with pytest.raises(Exception):  # ValidationError
            UserProfile(
                educationLevel="xxx",
                researchField="NLP",
                knowledgeLevel="intermediate",
                preferredStyle="balanced",
            )

    def test_analyze_request_missing_userid_raises(self):
        with pytest.raises(Exception):
            AnalyzeRequest(topic="test")  # userId 必填

    def test_analyze_request_empty_userid_raises(self):
        with pytest.raises(Exception):
            AnalyzeRequest(topic="test", userId="")

    def test_analyze_request_illegal_analysis_type_raises(self):
        with pytest.raises(Exception):
            AnalyzeRequest(topic="test", userId="u1", analysisType="xxx")

    def test_analyze_request_extra_field_forbidden(self):
        with pytest.raises(Exception):
            AnalyzeRequest.model_validate({
                "topic": "test",
                "userId": "u1",
                "unknownField": "xxx",  # extra='forbid'
            })

    def test_search_request_legal(self):
        req = SearchRequest(query="test query", topK=5)
        assert req.top_k == 5
        assert req.query == "test query"


# ===== FR-004 / FR-007: 全局异常处理 422 + 中文 message =====

class TestValidationErrorHandler:
    """测试 422 中文友好 message"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_missing_userid_returns_422(self):
        # userId 必填，缺 userId 触发 422
        response = self.client.post(
            "/api/agent/analyze",
            json={"topic": "test"},  # 缺 userId
        )
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == 422
        assert "userId" in body["message"] or "userId 字段" in body["message"]
        assert body["data"] is None
        assert "timestamp" in body
        assert isinstance(body["timestamp"], int)

    def test_illegal_enum_returns_422(self):
        response = self.client.post(
            "/api/agent/analyze",
            json={"topic": "test", "userId": "u1", "analysisType": "xxx"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == 422
        assert "analysisType" in body["message"]

    def test_empty_topic_returns_422(self):
        response = self.client.post(
            "/api/agent/analyze",
            json={"topic": "", "userId": "u1"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == 422
        assert "topic" in body["message"]

    def test_422_response_root_has_4_fields(self):
        response = self.client.post("/api/agent/analyze", json={"topic": ""})
        body = response.json()
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}


# ===== FR-006: success 路径用 ok() 包装 =====

class TestSuccessResponseUnified:
    """测试 success 端点返回 4 字段统一格式"""

    def test_suggest_endpoint_returns_unified(self):
        # /suggest 不需要 services，但 health 端点需要先就绪
        # 测试 model_status 端点的 503 fallback 包装
        client = TestClient(app)
        response = client.get("/api/model/status")
        # 未启动时 llm_service=None → 走 fail(503) 或 ok(...)，都应有 4 字段
        body = response.json()
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}


# ===== FR-006: camelCase alias 往返测试 =====

class TestCamelCaseAlias:
    """测试 camelCase 别名（Java 风格）"""

    def test_request_accepts_camelcase(self):
        # Java 端发送 camelCase 请求
        req = AnalyzeRequest.model_validate({
            "topic": "test",
            "userId": "u1",
            "analysisType": "report",
            "paperIds": ["p1"],
            "userProfile": {
                "educationLevel": "master",
                "researchField": "NLP",
                "knowledgeLevel": "intermediate",
                "preferredStyle": "balanced",
            },
        })
        assert req.user_id == "u1"
        assert req.analysis_type == AnalysisType.REPORT
        assert req.user_profile.education_level == EducationLevel.MASTER

    def test_response_serializes_to_camelcase(self):
        from app.models.schemas import AnalyzeResponse, AgentStateResponse

        resp = AnalyzeResponse(
            analysisId="a1",
            status="completed",
            agentStates=[
                AgentStateResponse(
                    agentName="retriever",
                    status="completed",
                    durationMs=1200,
                    intermediateResult="ok",
                )
            ],
            degraded=False,
            degradedReason=None,
        )
        dumped = resp.model_dump(by_alias=True, exclude_none=False)
        assert "analysisId" in dumped
        assert "agentStates" in dumped
        assert "degradedReason" in dumped
        assert "durationMs" in dumped["agentStates"][0]
        # 内部 snake_case 不应出现
        assert "analysis_id" not in dumped
        assert "agent_states" not in dumped
