package xiaozhi.modules.model.service;

import java.util.List;

import xiaozhi.modules.model.dto.ModelProviderDTO;
import xiaozhi.modules.model.dto.ModelProviderFieldDTO;
import xiaozhi.modules.model.entity.ModelProviderEntity;

public interface ModelProviderService {

    // List<String> getModelNames(String modelType, String modelName);

    List<ModelProviderDTO> getListByModelType(String modelType);

    ModelProviderDTO add(ModelProviderEntity modelProviderEntity);

    ModelProviderDTO edit(ModelProviderEntity modelProviderEntity);

    void delete();

    List<ModelProviderDTO> getList(String modelType, String provideCode);

    List<ModelProviderFieldDTO> getFieldList(String modelType, String provideCode);
}
