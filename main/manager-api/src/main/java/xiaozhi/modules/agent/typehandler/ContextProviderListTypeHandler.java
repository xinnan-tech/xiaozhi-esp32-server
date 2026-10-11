package xiaozhi.modules.agent.typehandler;

import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Collections;
import java.util.List;

import org.apache.commons.lang3.StringUtils;
import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;

import com.fasterxml.jackson.core.type.TypeReference;

import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dto.ContextProviderDTO;

/**
 * JSON type handler for context providers.
 *
 * <p>Do not extend MyBatis-Plus {@code AbstractJsonTypeHandler}: its constructor and JSON handler
 * contract changed in MyBatis-Plus 3.5.6. {@link BaseTypeHandler} is part of MyBatis itself and
 * keeps this handler compatible with both 3.5.5 and newer MyBatis-Plus releases.</p>
 */
public class ContextProviderListTypeHandler extends BaseTypeHandler<List<ContextProviderDTO>> {
    private static final TypeReference<List<ContextProviderDTO>> CONTEXT_PROVIDER_LIST_TYPE = new TypeReference<>() {
    };

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, List<ContextProviderDTO> parameter,
            JdbcType jdbcType) throws SQLException {
        ps.setString(i, JsonUtils.toJsonString(parameter));
    }

    @Override
    public List<ContextProviderDTO> getNullableResult(ResultSet rs, String columnName) throws SQLException {
        return parseNullable(rs.getString(columnName));
    }

    @Override
    public List<ContextProviderDTO> getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        return parseNullable(rs.getString(columnIndex));
    }

    @Override
    public List<ContextProviderDTO> getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        return parseNullable(cs.getString(columnIndex));
    }

    private List<ContextProviderDTO> parseNullable(String json) {
        if (StringUtils.isBlank(json)) {
            return null;
        }
        List<ContextProviderDTO> providers = JsonUtils.parseObject(json, CONTEXT_PROVIDER_LIST_TYPE);
        return providers == null ? Collections.emptyList() : providers;
    }

}
