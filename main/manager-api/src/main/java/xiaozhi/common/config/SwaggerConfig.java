package xiaozhi.common.config;

import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;

/**
 * Swagger Configuration
 * Copyright (c) RenRen Open Source All rights reserved.
 * Website: https://www.renren.io
 */
@Configuration
public class SwaggerConfig {

    @Bean
    public GroupedOpenApi deviceApi() {
        return GroupedOpenApi.builder()
                .group("device")
                .pathsToMatch("/device/**")
                .build();
    }

    @Bean
    public GroupedOpenApi agentApi() {
        return GroupedOpenApi.builder()
                .group("agent")
                .pathsToMatch("/agent/**")
                .build();
    }

    @Bean
    public GroupedOpenApi modelApi() {
        return GroupedOpenApi.builder()
                .group("models")
                .pathsToMatch("/models/**")
                .build();
    }

    @Bean
    public GroupedOpenApi oatApi() {
        return GroupedOpenApi.builder()
                .group("ota")
                .pathsToMatch("/ota/**")
                .build();
    }

    @Bean
    public GroupedOpenApi timbreApi() {
        return GroupedOpenApi.builder()
                .group("timbre")
                .pathsToMatch("/ttsVoice/**")
                .build();
    }

    @Bean
    public GroupedOpenApi sysApi() {
        return GroupedOpenApi.builder()
                .group("admin")
                .pathsToMatch("/admin/**")
                .build();
    }

    @Bean
    public GroupedOpenApi userApi() {
        return GroupedOpenApi.builder()
                .group("user")
                .pathsToMatch("/user/**")
                .build();
    }

    @Bean
    public GroupedOpenApi configApi() {
        return GroupedOpenApi.builder()
                .group("config")
                .pathsToMatch("/config/**")
                .build();
    }

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI().info(new Info()
                .title("Xiaozhi ESP32 Manager API")
                .description("Xiaozhi ESP32 Manager API Documentation")
                .version("3.0")
                .termsOfService("https://127.0.0.1"));
    }
}