package xiaozhi.common.handler;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.user.UserDetail;
import xiaozhi.modules.security.user.SecurityUser;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import java.util.Date;

/**
 * 公共字段，自动填充值
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Component
public class FieldMetaObjectHandler implements MetaObjectHandler {
    private final static String CREATE_DATE = "createDate";
    private final static String CREATOR = "creator";
    private final static String UPDATE_DATE = "updateDate";
    private final static String UPDATER = "updater";

    private final static String DATA_OPERATION = "dataOperation";
    private final static String DEPT_ID = "deptId";

    @Override
    public void insertFill(MetaObject metaObject) {
        UserDetail user = SecurityUser.getUser();
        Date date = new Date();

        //创建者
        strictInsertFill(metaObject, CREATOR, Long.class, user.getId());
        //创建时间
        strictInsertFill(metaObject, CREATE_DATE, Date.class, date);

        //创建者所属部门
        strictInsertFill(metaObject, DEPT_ID, Long.class, user.getDeptId());

        //更新者
        strictInsertFill(metaObject, UPDATER, Long.class, user.getId());
        //更新时间
        strictInsertFill(metaObject, UPDATE_DATE, Date.class, date);

        //数据标识
        strictInsertFill(metaObject, DATA_OPERATION, String.class, Constant.DataOperation.INSERT.getValue());
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        //更新者
        strictUpdateFill(metaObject, UPDATER, Long.class, SecurityUser.getUserId());
        //更新时间
        strictUpdateFill(metaObject, UPDATE_DATE, Date.class, new Date());

        //数据标识
        strictInsertFill(metaObject, DATA_OPERATION, String.class, Constant.DataOperation.UPDATE.getValue());
    }
}