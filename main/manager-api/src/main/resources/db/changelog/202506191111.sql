/*
 Navicat Premium Dump SQL

 Source Server         : 106服务器mysql
 Source Server Type    : MySQL
 Source Server Version : 80041 (8.0.41-0ubuntu0.24.04.1)
 Source Host           : 106.75.77.213:3306
 Source Schema         : xiaozhi_esp32_server

 Target Server Type    : MySQL
 Target Server Version : 80041 (8.0.41-0ubuntu0.24.04.1)
 File Encoding         : 65001

 Date: 19/06/2025 11:11:06
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for zy_ai_device_detail
-- ----------------------------
DROP TABLE IF EXISTS `zy_ai_device_detail`;
CREATE TABLE `zy_ai_device_detail`  (
  `id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `toy_type` int NULL DEFAULT NULL COMMENT '玩具形式（zy_ai_device_type_list的id）',
  `usermark` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL COMMENT '咨询者唯一标识',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
