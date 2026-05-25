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
    @DisplayName("paperListKey should return correct format")
    void shouldReturnCorrectPaperListKey() {
        assertEquals("paper:list:a1b2c3", RedisKeyUtil.paperListKey("a1b2c3"));
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
    @DisplayName("authBlacklistKey should return correct format")
    void shouldReturnCorrectAuthBlacklistKey() {
        assertEquals("auth:blacklist:abc123", RedisKeyUtil.authBlacklistKey("abc123"));
    }
}
