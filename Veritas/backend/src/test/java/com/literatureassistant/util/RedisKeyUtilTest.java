package com.literatureassistant.util;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class RedisKeyUtilTest {

    @Test
    @DisplayName("userProfileKey should return correct format")
    void shouldReturnCorrectUserProfileKey() {
        assertEquals("user:profile:usr_001", RedisKeyUtil.userProfileKey("usr_001"));
    }

    @Test
    @DisplayName("userProfileJsonKey should return correct format (task32)")
    void shouldReturnCorrectUserProfileJsonKey() {
        assertEquals("user:profile:json:usr_001", RedisKeyUtil.userProfileJsonKey("usr_001"));
    }

    @Test
    @DisplayName("userInfoKey should return correct format")
    void shouldReturnCorrectUserInfoKey() {
        assertEquals("user:info:usr_001", RedisKeyUtil.userInfoKey("usr_001"));
    }

    @Test
    @DisplayName("paperDetailKey should return correct format")
    void shouldReturnCorrectPaperDetailKey() {
        assertEquals("paper:detail:arxiv_001", RedisKeyUtil.paperDetailKey("arxiv_001"));
    }

    @Test
    @DisplayName("paperListKey should return correct format (task33: page+size 参数)")
    void shouldReturnCorrectPaperListKey() {
        assertEquals("paper:list:1:10", RedisKeyUtil.paperListKey(1, 10));
    }

    @Test
    @DisplayName("paperSearchKey should return correct format (task35: 9 参数复合 Key)")
    void shouldReturnCorrectPaperSearchKey() {
        String key = RedisKeyUtil.paperSearchKey("transformer", 2020, 2024,
                "AAAI", "Wang", "deep-learning", "relevance", "desc", 1, 10);
        assertEquals("paper:search:transformer_2020_2024_AAAI_Wang_deep-learning_relevance_desc_1_10", key);
    }

    @Test
    @DisplayName("paperSearchKey should handle null params (task33: null→all/empty)")
    void shouldHandleNullParamsInPaperSearchKey() {
        String key = RedisKeyUtil.paperSearchKey(null, null, null, null, null, null, null, null, 1, 10);
        // q=null→""(空), yearFrom/yearTo/venue/author/keywords=null→"all", sort=null→"relevance", sortDirection=null→"desc"
        assertEquals("paper:search:_all_all_all_all_all_relevance_desc_1_10", key);
    }

    @Test
    @DisplayName("sessionListKey should return correct format (task34)")
    void shouldReturnCorrectSessionListKey() {
        assertEquals("session:list:usr_001:1:10", RedisKeyUtil.sessionListKey("usr_001", 1, 10));
    }

    @Test
    @DisplayName("favoriteListKey should return correct format (task36)")
    void shouldReturnCorrectFavoriteListKey() {
        assertEquals("user:favorites:usr_001", RedisKeyUtil.favoriteListKey("usr_001"));
    }

    @Test
    @DisplayName("searchResultKey should return correct format")
    void shouldReturnCorrectSearchResultKey() {
        assertEquals("search:result:a1b2c3", RedisKeyUtil.searchResultKey("a1b2c3"));
    }

    @Test
    @DisplayName("analysisResultKey should return correct format")
    void shouldReturnCorrectAnalysisResultKey() {
        assertEquals("analysis:result:anl_001", RedisKeyUtil.analysisResultKey("anl_001"));
    }

    @Test
    @DisplayName("sessionStateKey should return correct format")
    void shouldReturnCorrectSessionStateKey() {
        assertEquals("session:state:ses_001", RedisKeyUtil.sessionStateKey("ses_001"));
    }

    @Test
    @DisplayName("agentStateKey should return correct format")
    void shouldReturnCorrectAgentStateKey() {
        assertEquals("agent:state:anl_001", RedisKeyUtil.agentStateKey("anl_001"));
    }

    @Test
    @DisplayName("agentFallbackKey should return correct format")
    void shouldReturnCorrectAgentFallbackKey() {
        assertEquals("agent:fallback:anl_001", RedisKeyUtil.agentFallbackKey("anl_001"));
    }

    @Test
    @DisplayName("authBlacklistKey should return correct format")
    void shouldReturnCorrectAuthBlacklistKey() {
        assertEquals("auth:blacklist:abc123", RedisKeyUtil.authBlacklistKey("abc123"));
    }
}
