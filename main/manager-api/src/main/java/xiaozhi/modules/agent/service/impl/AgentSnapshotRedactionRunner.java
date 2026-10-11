package xiaozhi.modules.agent.service.impl;

import java.util.concurrent.TimeUnit;

import org.springframework.beans.factory.SmartInitializingSingleton;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.agent.service.AgentSnapshotService;

@Slf4j
@Component
@RequiredArgsConstructor
public class AgentSnapshotRedactionRunner implements SmartInitializingSingleton {
    static final long ROLLING_DEPLOYMENT_INITIAL_DELAY_MILLIS = 5_000;
    static final long ROLLING_DEPLOYMENT_FIXED_DELAY_MILLIS = 15_000;

    private final AgentSnapshotService agentSnapshotService;

    @Override
    public void afterSingletonsInstantiated() {
        redactAndReport("startup");
    }

    @Scheduled(initialDelay = ROLLING_DEPLOYMENT_INITIAL_DELAY_MILLIS,
            fixedDelay = ROLLING_DEPLOYMENT_FIXED_DELAY_MILLIS)
    public void redactLateRollingDeploymentWrites() {
        redactAndReport("rolling-deployment");
    }

    private void redactAndReport(String trigger) {
        long startedAt = System.nanoTime();
        try {
            long migrated = agentSnapshotService.redactLegacySnapshots();
            long durationMillis = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startedAt);
            if (migrated > 0) {
                log.warn("Agent snapshot legacy redaction trigger={} migrated={} durationMs={}. Rotate credentials "
                        + "that may have appeared in historical snapshot URLs, cookies, sessions, or structured "
                        + "headers.", trigger, migrated, durationMillis);
            } else if ("startup".equals(trigger)) {
                log.info("Agent snapshot legacy redaction startup pass completed: migrated=0 durationMs={}; "
                        + "rolling-deployment compensation starts after {} ms and repeats every {} ms.",
                        durationMillis, ROLLING_DEPLOYMENT_INITIAL_DELAY_MILLIS,
                        ROLLING_DEPLOYMENT_FIXED_DELAY_MILLIS);
            }
        } catch (RuntimeException exception) {
            if ("startup".equals(trigger)) {
                log.error("Agent snapshot legacy redaction failed during startup; blocking application startup "
                        + "before it can accept traffic.", exception);
            } else {
                log.error("Agent snapshot legacy redaction failed during rolling-deployment compensation; the "
                        + "scheduler will retry on its next run.", exception);
            }
            throw exception;
        }
    }
}
