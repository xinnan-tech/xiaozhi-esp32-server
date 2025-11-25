package xiaozhi.modules.knowledge.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapterFactory;

/**
 * 知识库配置类
 * 配置知识库相关的Bean
 */
@Configuration
public class KnowledgeBaseConfig {

    /**
     * 提供KnowledgeBaseAdapterFactory的Bean实例
     * @return KnowledgeBaseAdapterFactory实例
     */
    @Bean
    public KnowledgeBaseAdapterFactory knowledgeBaseAdapterFactory() {
        return new KnowledgeBaseAdapterFactory();
    }
}