package com.literatureassistant.util;

public final class RedisKeyUtil {

    private RedisKeyUtil() {
    }

    public static String userProfileKey(String userId) {
        return "user:profile:" + userId;
    }

    public static String userInfoKey(String userId) {
        return "user:info:" + userId;
    }

    public static String paperDetailKey(String paperId) {
        return "paper:detail:" + paperId;
    }

    public static String paperListKey(String queryHash) {
        return "paper:list:" + queryHash;
    }

    public static String searchResultKey(String queryHash) {
        return "search:result:" + queryHash;
    }

    public static String analysisResultKey(String analysisId) {
        return "analysis:result:" + analysisId;
    }

    public static String sessionStateKey(String sessionId) {
        return "session:state:" + sessionId;
    }

    public static String agentStateKey(String analysisId) {
        return "agent:state:" + analysisId;
    }

    public static String agentFallbackKey(String analysisId) {
        return "agent:fallback:" + analysisId;
    }

    public static String authBlacklistKey(String tokenHash) {
        return "auth:blacklist:" + tokenHash;
    }
}
