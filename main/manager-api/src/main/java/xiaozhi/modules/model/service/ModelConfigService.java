package xiaozhi.modules.model.service;

import java.util.List;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.model.dto.ModelBasicInfoDTO;
import xiaozhi.modules.model.dto.ModelConfigBodyDTO;
import xiaozhi.modules.model.dto.ModelConfigDTO;
import xiaozhi.modules.model.entity.ModelConfigEntity;

public interface ModelConfigService extends BaseService<ModelConfigEntity> {

    List<ModelBasicInfoDTO> getModelCodeList(String modelType, String modelName);

    PageData<ModelConfigDTO> getPageList(String modelType, String modelName, String page, String limit);

    ModelConfigDTO add(String modelType, String provideCode, ModelConfigBodyDTO modelConfigBodyDTO);

    ModelConfigDTO edit(String modelType, String provideCode, String id, ModelConfigBodyDTO modelConfigBodyDTO);

    void delete(String id);

    /**
     * IDによりモデル名を取得
     * 
     * @param id モデルID
     * @return モデル名
     */
    String getModelNameById(String id);

    /**
     * IDによりモデル設定を取得
     * 
     * @param id      モデルID
     * @param isCache キャッシュするかどうか
     * @return モデル設定エンティティ
     */
    ModelConfigEntity getModelById(String id, boolean isCache);

    /**
     * デフォルトモデルを設定
     * 
     * @param modelType モデルタイプ
     * @param isDefault デフォルトかどうか
     */
    void setDefaultModel(String modelType, int isDefault);
}
