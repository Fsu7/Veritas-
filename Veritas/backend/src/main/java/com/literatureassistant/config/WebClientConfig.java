package com.literatureassistant.config;

import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import io.netty.handler.timeout.WriteTimeoutHandler;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.ExchangeStrategies;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;
import reactor.netty.resources.ConnectionProvider;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

@Configuration
public class WebClientConfig {

    @Value("${ai-service.url}")
    private String aiServiceUrl;

    /**
     * 同步调用 WebClient (30s 响应超时)，用于 analyze/search/model-status。
     */
    @Bean
    public WebClient webClient() {
        ConnectionProvider connectionProvider = ConnectionProvider.builder("ai-service-pool")
                .maxConnections(50)
                .pendingAcquireTimeout(Duration.ofSeconds(30))
                .build();

        HttpClient httpClient = HttpClient.create(connectionProvider)
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)
                .responseTimeout(Duration.ofSeconds(30))
                .doOnConnected(conn -> conn
                        .addHandlerLast(new ReadTimeoutHandler(30, TimeUnit.SECONDS))
                        .addHandlerLast(new WriteTimeoutHandler(30, TimeUnit.SECONDS)));

        ExchangeStrategies exchangeStrategies = ExchangeStrategies.builder()
                .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(16 * 1024 * 1024))
                .build();

        return WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .exchangeStrategies(exchangeStrategies)
                .baseUrl(aiServiceUrl)
                .build();
    }

    /**
     * SSE 流式调用 WebClient (120s 响应超时，task29 从 150s 调整为 120s 对齐 JM4 检查点)，用于 /api/agent/{analyze|compare|report}/stream。
     * <p>独立连接池与超时，避免与同步客户端互相影响。
     */
    @Bean("sseWebClient")
    public WebClient sseWebClient() {
        ConnectionProvider connectionProvider = ConnectionProvider.builder("ai-service-sse-pool")
                .maxConnections(20)
                .pendingAcquireTimeout(Duration.ofSeconds(60))
                .build();

        HttpClient httpClient = HttpClient.create(connectionProvider)
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)
                .responseTimeout(Duration.ofSeconds(120))
                .doOnConnected(conn -> conn
                        .addHandlerLast(new ReadTimeoutHandler(120, TimeUnit.SECONDS))
                        .addHandlerLast(new WriteTimeoutHandler(30, TimeUnit.SECONDS)));

        // 注册 SSE 事件解码器（Spring 6.x 默认开启 text/event-stream 解码）
        ExchangeStrategies exchangeStrategies = ExchangeStrategies.builder()
                .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(16 * 1024 * 1024))
                .build();

        return WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .exchangeStrategies(exchangeStrategies)
                .baseUrl(aiServiceUrl)
                .defaultHeader("Accept", MediaType.TEXT_EVENT_STREAM_VALUE)
                .build();
    }
}
