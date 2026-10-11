package xiaozhi.common.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.CALLS_REAL_METHODS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.function.BiFunction;

import org.apache.ibatis.binding.MapperMethod;
import org.apache.ibatis.executor.BatchResult;
import org.apache.ibatis.logging.nologging.NoLoggingImpl;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.session.ExecutorType;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import com.baomidou.mybatisplus.core.enums.SqlMethod;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.toolkit.SqlHelper;

class BaseServiceImplTest {
    private static final String INSERT_STATEMENT = TestMapper.class.getName() + ".insert";
    private static final String UPDATE_STATEMENT = TestMapper.class.getName() + ".updateById";

    private final TestService service = new TestService();

    @AfterEach
    void clearTransactionSynchronization() {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void insertBatchFlushesAtTheRequestedBatchSizeAndCommitsWithoutATransaction() {
        SqlSessionFactory sqlSessionFactory = mock(SqlSessionFactory.class);
        SqlSession sqlSession = mock(SqlSession.class);
        when(sqlSessionFactory.openSession(ExecutorType.BATCH)).thenReturn(sqlSession);
        when(sqlSession.insert(eq(INSERT_STATEMENT), any(TestEntity.class))).thenReturn(1);
        when(sqlSession.flushStatements())
                .thenReturn(List.of(batchResult(1, 1)))
                .thenReturn(List.of(batchResult(1)));

        TestEntity first = new TestEntity(1L);
        TestEntity second = new TestEntity(2L);
        TestEntity third = new TestEntity(3L);

        try (MockedStatic<SqlHelper> sqlHelper = sqlHelperUsing(sqlSessionFactory)) {
            assertTrue(service.insertBatch(List.of(first, second, third), 2));
        }

        verify(sqlSession).insert(INSERT_STATEMENT, first);
        verify(sqlSession).insert(INSERT_STATEMENT, second);
        verify(sqlSession).insert(INSERT_STATEMENT, third);
        verify(sqlSession, times(2)).flushStatements();
        verify(sqlSession).commit(true);
        verify(sqlSession).close();
    }

    @Test
    void updateBatchByIdPassesEachEntityAndReturnsSuccessfulFlushResult() {
        SqlSessionFactory sqlSessionFactory = mock(SqlSessionFactory.class);
        SqlSession sqlSession = mock(SqlSession.class);
        when(sqlSessionFactory.openSession(ExecutorType.BATCH)).thenReturn(sqlSession);
        when(sqlSession.update(eq(UPDATE_STATEMENT), any())).thenReturn(1);
        when(sqlSession.flushStatements()).thenReturn(List.of(batchResult(1, 1)));

        TestEntity first = new TestEntity(1L);
        TestEntity second = new TestEntity(2L);

        try (MockedStatic<SqlHelper> sqlHelper = sqlHelperUsing(sqlSessionFactory)) {
            assertTrue(service.updateBatchById(List.of(first, second), 10));
        }

        ArgumentCaptor<Object> params = ArgumentCaptor.forClass(Object.class);
        verify(sqlSession, times(2)).update(eq(UPDATE_STATEMENT), params.capture());
        assertSame(first, entityFrom(params.getAllValues().get(0)));
        assertSame(second, entityFrom(params.getAllValues().get(1)));
        verify(sqlSession).flushStatements();
    }

    @Test
    void batchCallbacksReturnActualAffectedRowCounts() {
        SqlSession sqlSession = mock(SqlSession.class);
        when(sqlSession.insert(eq(INSERT_STATEMENT), any(TestEntity.class))).thenReturn(3);
        when(sqlSession.update(eq(UPDATE_STATEMENT), any())).thenReturn(2);
        CallbackCapturingTestService capturingService = new CallbackCapturingTestService(sqlSession);
        TestEntity entity = new TestEntity(1L);

        assertTrue(capturingService.insertBatch(List.of(entity), 7));
        assertEquals(7, capturingService.batchSize);
        assertEquals(List.of(3), capturingService.affectedRows);

        assertTrue(capturingService.updateBatchById(List.of(entity), 9));
        assertEquals(9, capturingService.batchSize);
        assertEquals(List.of(2), capturingService.affectedRows);
    }

    @Test
    void emptyBatchesReturnFalseWithoutOpeningABatchSession() {
        SqlSessionFactory sqlSessionFactory = mock(SqlSessionFactory.class);

        try (MockedStatic<SqlHelper> sqlHelper = sqlHelperUsing(sqlSessionFactory)) {
            assertFalse(service.insertBatch(List.of(), 10));
            assertFalse(service.updateBatchById(List.of(), 10));
        }

        verifyNoInteractions(sqlSessionFactory);
    }

    @Test
    void deleteBatchIdsDelegatesToCompatibleApiAndPreservesAffectedRowResult() {
        TestMapper mapper = mock(TestMapper.class);
        List<Long> ids = List.of(1L, 2L);
        service.baseDao = mapper;
        when(mapper.deleteByIds(ids)).thenReturn(2).thenReturn(0);

        assertTrue(service.deleteBatchIds(ids));
        assertFalse(service.deleteBatchIds(ids));

        verify(mapper, times(2)).deleteByIds(ids);
    }

    @Test
    void activeTransactionSynchronizationUsesTransactionAwareCommitAndLifecycle() {
        SqlSessionFactory sqlSessionFactory = mock(SqlSessionFactory.class);
        SqlSession sqlSession = mock(SqlSession.class);
        when(sqlSessionFactory.openSession(ExecutorType.BATCH)).thenReturn(sqlSession);
        when(sqlSession.insert(eq(INSERT_STATEMENT), any(TestEntity.class))).thenReturn(1);
        when(sqlSession.flushStatements()).thenReturn(List.of(batchResult(1)));
        TransactionSynchronizationManager.initSynchronization();

        try (MockedStatic<SqlHelper> sqlHelper = sqlHelperUsing(sqlSessionFactory)) {
            assertTrue(service.insertBatch(List.of(new TestEntity(1L)), 1));
        }

        verify(sqlSession).flushStatements();
        verify(sqlSession).commit(false);
        verify(sqlSession, never()).commit(true);
        verify(sqlSession, never()).close();
    }

    @SuppressWarnings("deprecation")
    private static MockedStatic<SqlHelper> sqlHelperUsing(SqlSessionFactory sqlSessionFactory) {
        MockedStatic<SqlHelper> sqlHelper = mockStatic(SqlHelper.class, CALLS_REAL_METHODS);
        sqlHelper.when(() -> SqlHelper.sqlSessionFactory(TestEntity.class)).thenReturn(sqlSessionFactory);
        return sqlHelper;
    }

    private static BatchResult batchResult(int... updateCounts) {
        BatchResult result = new BatchResult(mock(MappedStatement.class), "batch");
        result.setUpdateCounts(updateCounts);
        return result;
    }

    private static Object entityFrom(Object parameter) {
        assertTrue(parameter instanceof MapperMethod.ParamMap<?>);
        return ((Map<?, ?>) parameter).get(Constants.ENTITY);
    }

    private interface TestMapper extends BaseMapper<TestEntity> {
    }

    private record TestEntity(Long id) {
    }

    private static class TestService extends BaseServiceImpl<TestMapper, TestEntity> {
        private TestService() {
            log = new NoLoggingImpl(TestService.class.getName());
        }

        @Override
        protected String getSqlStatement(SqlMethod sqlMethod) {
            return switch (sqlMethod) {
                case INSERT_ONE -> INSERT_STATEMENT;
                case UPDATE_BY_ID -> UPDATE_STATEMENT;
                default -> throw new IllegalArgumentException("Unexpected SQL method: " + sqlMethod);
            };
        }
    }

    private static class CallbackCapturingTestService extends TestService {
        private final SqlSession sqlSession;
        private int batchSize;
        private List<Integer> affectedRows;

        private CallbackCapturingTestService(SqlSession sqlSession) {
            this.sqlSession = sqlSession;
        }

        @Override
        protected <E> boolean executeBatch(Collection<E> list, int batchSize,
                BiFunction<SqlSession, E, Integer> operation) {
            this.batchSize = batchSize;
            this.affectedRows = list.stream().map(entity -> operation.apply(sqlSession, entity)).toList();
            return true;
        }
    }
}
