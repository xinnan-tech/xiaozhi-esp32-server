package xiaozhi.modules.model.service;

import xiaozhi.modules.model.dto.ModelProviderDTO;
import xiaozhi.modules.model.entity.ModelProviderEntity;

import java.util.List;

public interface ModelProviderService {

//    List<String> getModelNames(String modelType, String modelName);

    List<ModelProviderDTO> getListByModelType(String modelType);

    ModelProviderDTO add(ModelProviderEntity modelProviderEntity);

    ModelProviderDTO edit(ModelProviderEntity modelProviderEntity);

    void delete();

    List<ModelProviderDTO> getList(String modelType, String provideCode);

    List<String> getFieldList(String modelType, String provideCode);
}
