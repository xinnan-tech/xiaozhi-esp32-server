package xiaozhi.modules.sys.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.DependsOn;

import jakarta.annotation.PostConstruct;
import xiaozhi.modules.sys.service.SysParamsService;

@Configuration
@DependsOn("liquibase")
public class SystemInitConfig {

    @Autowired
    private SysParamsService sysParamsService;

    @PostConstruct
    public void init() {
        sysParamsService.initServerSecret();
    }
}