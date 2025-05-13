package xiaozhi.common.service.impl;

import java.io.Serializable;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import org.springframework.beans.BeanUtils;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.ReflectionKit;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.CrudService;
import xiaozhi.common.utils.ConvertUtils;

/**
 * CRUD基础服务类
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public abstract class CrudServiceImpl<M extends BaseMapper<T>, T, D> extends BaseServiceImpl<M, T>
        implements CrudService<T, D> {

    protected Class<D> currentDtoClass() {
        return (Class<D>) ReflectionKit.getSuperClassGenericType(getClass(), CrudServiceImpl.class, 2);
    }

    @Override
    public PageData<D> page(Map<String, Object> params) {
        IPage<T> page = baseDao.selectPage(
                getPage(params, null, false),
                getWrapper(params));

        return getPageData(page, currentDtoClass());
    }

    @Override
    public List<D> list(Map<String, Object> params) {
        List<T> entityList = baseDao.selectList(getWrapper(params));

        return ConvertUtils.sourceToTarget(entityList, currentDtoClass());
    }

    public abstract QueryWrapper<T> getWrapper(Map<String, Object> params);

    @Override
    public D get(Serializable id) {
        T entity = baseDao.selectById(id);

        return ConvertUtils.sourceToTarget(entity, currentDtoClass());
    }

    @Override
    public void save(D dto) {
        T entity = ConvertUtils.sourceToTarget(dto, currentModelClass());
        insert(entity);

        // copy主键值到dto
        BeanUtils.copyProperties(entity, dto);
    }

    @Override
    public void update(D dto) {
        T entity = ConvertUtils.sourceToTarget(dto, currentModelClass());
        updateById(entity);
    }

    @Override
    public void delete(Serializable[] ids) {
        baseDao.deleteBatchIds(Arrays.asList(ids));
    }
}