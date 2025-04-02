package xiaozhi.common.service;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;

/**
 * CRUD基础服务接口
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public interface CrudService<T, D> extends BaseService<T> {

    PageData<D> page(Map<String, Object> params);

    List<D> list(Map<String, Object> params);

    D get(Serializable id);

    void save(D dto);

    void update(D dto);

    void delete(Serializable[] ids);

}