package xiaozhi.modules.agent.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.lang.reflect.Method;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.SmartInitializingSingleton;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.scheduling.annotation.Scheduled;

import xiaozhi.modules.agent.service.AgentSnapshotService;

@ExtendWith(OutputCaptureExtension.class)
class AgentSnapshotRedactionRunnerTest {

    @Test
    void startupRedactionRunsSynchronouslyAndReportsCompensationWindow(CapturedOutput output) {
        assertTrue(SmartInitializingSingleton.class.isAssignableFrom(AgentSnapshotRedactionRunner.class));
        AgentSnapshotService service = mock(AgentSnapshotService.class);
        AgentSnapshotRedactionRunner runner = new AgentSnapshotRedactionRunner(service);
        when(service.redactLegacySnapshots()).thenReturn(0L);

        runner.afterSingletonsInstantiated();

        verify(service).redactLegacySnapshots();
        assertTrue(output.getAll().contains("startup pass completed"));
        assertTrue(output.getAll().contains("starts after 5000 ms and repeats every 15000 ms"));
    }

    @Test
    void startupRedactionFailureIsLoggedAndPropagatedToKeepStartupFailClosed(CapturedOutput output) {
        AgentSnapshotService service = mock(AgentSnapshotService.class);
        AgentSnapshotRedactionRunner runner = new AgentSnapshotRedactionRunner(service);
        IllegalStateException failure = new IllegalStateException("database unavailable");
        when(service.redactLegacySnapshots()).thenThrow(failure);

        IllegalStateException thrown = assertThrows(IllegalStateException.class,
                runner::afterSingletonsInstantiated);

        assertSame(failure, thrown);
        assertTrue(output.getAll().contains("blocking application startup before it can accept traffic"));
    }

    @Test
    void rollingDeploymentRedactionReportsTriggerCountAndCredentialRotation(CapturedOutput output) {
        AgentSnapshotService service = mock(AgentSnapshotService.class);
        AgentSnapshotRedactionRunner runner = new AgentSnapshotRedactionRunner(service);
        when(service.redactLegacySnapshots()).thenReturn(3L);

        runner.redactLateRollingDeploymentWrites();

        assertTrue(output.getAll().contains("trigger=rolling-deployment migrated=3"));
        assertTrue(output.getAll().contains("Rotate credentials"));
    }

    @Test
    void rollingDeploymentScheduleKeepsLegacyWriteExposureWindowShort() throws Exception {
        Method method = AgentSnapshotRedactionRunner.class.getMethod("redactLateRollingDeploymentWrites");
        Scheduled scheduled = method.getAnnotation(Scheduled.class);

        assertNotNull(scheduled);
        assertEquals(5_000, scheduled.initialDelay());
        assertEquals(15_000, scheduled.fixedDelay());
        assertTrue(scheduled.initialDelay() <= 10_000);
        assertTrue(scheduled.fixedDelay() <= 30_000);
    }
}
