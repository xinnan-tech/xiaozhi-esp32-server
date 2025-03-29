package xiaozhi.modules.model.service;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.model.dto.ModelConfigBodyDTO;
import xiaozhi.modules.model.dto.ModelConfigDTO;

import java.util.List;

public interface ModelConfigService {

    List<String> getModelCodeList(String modelType, String modelName);

    PageData<ModelConfigDTO> getPageList(String modelType, String modelName, Integer page, Integer limit);

    ModelConfigDTO add(String modelType, String provideCode, ModelConfigBodyDTO modelConfigBodyDTO);

    ModelConfigDTO edit(String modelType, String provideCode, String id, ModelConfigBodyDTO modelConfigBodyDTO);

    void delete(String modelType, String provideCode, String id);

    List<String> getVoiceList(String modelName, String voiceName);
}
