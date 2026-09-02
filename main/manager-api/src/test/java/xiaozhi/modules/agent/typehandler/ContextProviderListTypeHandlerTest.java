package xiaozhi.modules.agent.typehandler;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.List;

import org.apache.ibatis.type.TypeHandler;
import org.apache.ibatis.type.TypeHandlerRegistry;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.fasterxml.jackson.core.type.TypeReference;

import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dto.ContextProviderDTO;

class ContextProviderListTypeHandlerTest {

    private final ContextProviderListTypeHandler handler = new ContextProviderListTypeHandler();

    @Test
    void myBatisCanInstantiateHandlerForListField() {
        TypeHandler<?> typeHandler = new TypeHandlerRegistry().getInstance(List.class,
                ContextProviderListTypeHandler.class);

        assertInstanceOf(ContextProviderListTypeHandler.class, typeHandler);
    }

    @Test
    void resultSetDeserializationKeepsContextProviderDtoElementType() throws Exception {
        ResultSet resultSet = mock(ResultSet.class);
        when(resultSet.getString("context_providers"))
                .thenReturn("[{\"url\":\"https://example.com/context\",\"headers\":{\"Authorization\":\"Bearer token\"}}]");

        List<ContextProviderDTO> providers = handler.getNullableResult(resultSet, "context_providers");

        assertEquals(1, providers.size());
        assertInstanceOf(ContextProviderDTO.class, providers.get(0));
        assertEquals("https://example.com/context", providers.get(0).getUrl());
        assertEquals("Bearer token", providers.get(0).getHeaders().get("Authorization"));
    }

    @Test
    void sqlNullRemainsNull() throws Exception {
        ResultSet resultSet = mock(ResultSet.class);

        assertNull(handler.getNullableResult(resultSet, 1));
    }

    @Test
    void serializesProviderListAsJson() throws Exception {
        ContextProviderDTO provider = new ContextProviderDTO();
        provider.setUrl("https://example.com/context");
        PreparedStatement statement = mock(PreparedStatement.class);

        handler.setNonNullParameter(statement, 1, List.of(provider), null);

        ArgumentCaptor<String> json = ArgumentCaptor.forClass(String.class);
        verify(statement).setString(eq(1), json.capture());
        List<ContextProviderDTO> serialized = JsonUtils.parseObject(json.getValue(), new TypeReference<>() {
        });
        assertEquals(1, serialized.size());
        assertEquals("https://example.com/context", serialized.get(0).getUrl());
    }
}
