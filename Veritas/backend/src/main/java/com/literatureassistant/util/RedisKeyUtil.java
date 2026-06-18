package com.literatureassistant.util;

public final class RedisKeyUtil {

    private RedisKeyUtil() {
    }

    public static String userProfileKey(String userId) {
        return "user:profile:" + userId;
    }

    /**
     * task32: 用户画像 JSON Key（供 syncProfileToRedis 写入，Python AI 服务跨语言读取）。
     * <p>与 {@link #userProfileKey(String)} 区别：
     * <ul>
     *   <li>userProfileKey: Spring Cache @Cacheable(value="userProfile") 内部使用</li>
     *   <li>userProfileJsonKey: 手动 RedisTemplate 写入，供 Python 服务通过 Redis 读取画像</li>
     * </ul>
     */
    public static String userProfileJsonKey(String userId) {
        return "user:profile:json:" + userId;
    }

    public static String userInfoKey(String userId) {
        return "user:info:" + userId;
    }

    public static String paperDetailKey(String paperId) {
        return "paper:detail:" + paperId;
    }

    /**
     * task33: 论文搜索复合 Key（规范化生成，处理 null 参数避免拼成 "null" 字符串）。
     * <p>null 参数统一处理：yearFrom/yearTo/venue 为 null 时用 "all" 占位，q 为 null 时用空串。
     * <p>task35: 扩展为包含 author/keywords/sortDirection 参数（9 个参数），保证缓存 Key 隔离。
     */
    public static String paperSearchKey(String q, Integer yearFrom, Integer yearTo,
                                         String venue, String author, String keywords,
                                         String sort, String sortDirection, int page, int size) {
        String safeQ = q == null ? "" : q;
        String yf = yearFrom == null ? "all" : yearFrom.toString();
        String yt = yearTo == null ? "all" : yearTo.toString();
        String v = venue == null ? "all" : venue;
        String a = author == null ? "all" : author;
        String k = keywords == null ? "all" : keywords;
        String s = sort == null ? "relevance" : sort;
        String sd = sortDirection == null ? "desc" : sortDirection;
        return "paper:search:" + safeQ + "_" + yf + "_" + yt + "_" + v + "_" + a + "_" + k + "_" + s + "_" + sd + "_" + page + "_" + size;
    }

    public static String paperListKey(int page, int size) {
        return "paper:list:" + page + ":" + size;
    }

    /**
     * task34: 用户会话列表 Key（分页）。
     */
    public static String sessionListKey(String userId, int page, int size) {
        return "session:list:" + userId + ":" + page + ":" + size;
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

    /**
     * task36: 用户收藏列表 Key（不含分页，已废弃）。
     * <p>修复 B-002: 原 Key 缺 page/size 参数，导致不同分页查询命中同一缓存。
     * 请使用 {@link #favoriteListKey(String, int, int)} 替代。
     */
    @Deprecated
    public static String favoriteListKey(String userId) {
        return "user:favorites:" + userId;
    }

    /**
     * task36: 用户收藏列表 Key（含分页）。
     * <p>修复 B-002: Key 必须包含 page/size 参数，避免不同分页查询命中同一缓存。
     */
    public static String favoriteListKey(String userId, int page, int size) {
        return "user:favorites:" + userId + ":" + page + ":" + size;
    }
}
