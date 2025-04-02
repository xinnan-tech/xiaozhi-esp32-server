package xiaozhi.common.utils;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

import lombok.Data;

/**
 * 树节点，所有需要实现树节点的，都需要继承该类
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Data
public class TreeNode<T> implements Serializable {

    /**
     * 主键
     */
    private Long id;
    /**
     * 上级ID
     */
    private Long pid;
    /**
     * 子节点列表
     */
    private List<T> children = new ArrayList<>();

}