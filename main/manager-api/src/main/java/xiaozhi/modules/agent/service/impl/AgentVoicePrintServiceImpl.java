package xiaozhi.modules.agent.service.impl;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.List;
import java.util.concurrent.Executor;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentVoicePrintDao;
import xiaozhi.modules.agent.dto.AgentVoicePrintSaveDTO;
import xiaozhi.modules.agent.dto.AgentVoicePrintUpdateDTO;
import xiaozhi.modules.agent.dto.IdentifyVoicePrintResponse;
import xiaozhi.modules.agent.entity.AgentVoicePrintEntity;
import xiaozhi.modules.agent.service.AgentChatAudioService;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentVoicePrintService;
import xiaozhi.modules.agent.vo.AgentVoicePrintVO;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * @author zjy
 */
@Service
@Slf4j
public class AgentVoicePrintServiceImpl extends ServiceImpl<AgentVoicePrintDao, AgentVoicePrintEntity>
        implements AgentVoicePrintService {
    private final AgentChatAudioService agentChatAudioService;
    private final RestTemplate restTemplate;
    private final SysParamsService sysParamsService;
    private final AgentChatHistoryService agentChatHistoryService;
    // Springboot提供的编程事务类
    private final TransactionTemplate transactionTemplate;
    // 识别度
    private final Double RECOGNITION = 0.5;
    private final Executor taskExecutor;

    public AgentVoicePrintServiceImpl(AgentChatAudioService agentChatAudioService, RestTemplate restTemplate,
                                      SysParamsService sysParamsService, AgentChatHistoryService agentChatHistoryService,
                                      TransactionTemplate transactionTemplate, @Qualifier("taskExecutor") Executor taskExecutor) {
        this.agentChatAudioService = agentChatAudioService;
        this.restTemplate = restTemplate;
        this.sysParamsService = sysParamsService;
        this.agentChatHistoryService = agentChatHistoryService;
        this.transactionTemplate = transactionTemplate;
        this.taskExecutor = taskExecutor;
    }

    @Override
    public boolean insert(AgentVoicePrintSaveDTO dto) {
        // 获取音频数据
        ByteArrayResource resource = getVoicePrintAudioWAV(dto.getAgentId(), dto.getAudioId());
        // 识别一下此声音是否注册过
        IdentifyVoicePrintResponse response = identifyVoicePrint(dto.getAgentId(), resource);
        if (response != null && response.getScore() > RECOGNITION) {
            // 根据识别出的声纹ID查询对应的用户信息
            AgentVoicePrintEntity existingVoicePrint = baseMapper.selectById(response.getSpeakerId());
            String existingUserName = existingVoicePrint != null ? existingVoicePrint.getSourceName() : "未知用户";
            throw new RenException("此声音声纹对应的人（" + existingUserName + "）已经注册，请选择其他声音注册");
        }
        AgentVoicePrintEntity entity = ConvertUtils.sourceToTarget(dto, AgentVoicePrintEntity.class);
        // 开启事务
        return Boolean.TRUE.equals(transactionTemplate.execute(status -> {
            try {
                // 保存声纹信息
                int row = baseMapper.insert(entity);
                // 插入一条数据，影响的数据不等于1说明出现了，保存问题回滚
                if (row != 1) {
                    status.setRollbackOnly(); // 标记事务回滚
                    return false;
                }
                // 发送注册声纹请求
                registerVoicePrint(entity.getId(), resource);
                return true;
            } catch (RenException e) {
                status.setRollbackOnly(); // 标记事务回滚
                throw e;
            } catch (Exception e) {
                status.setRollbackOnly(); // 标记事务回滚
                log.error("保存声纹错误原因：{}", e.getMessage());
                throw new RenException("保存声纹错误，请联系管理员");
            }
        }));
    }

    @Override
    public boolean delete(Long userId, String voicePrintId) {
        // 开启事务
        boolean b = Boolean.TRUE.equals(transactionTemplate.execute(status -> {
            try {
                // 删除声纹,按照指定当前登录用户和智能体
                int row = baseMapper.delete(new LambdaQueryWrapper<AgentVoicePrintEntity>()
                        .eq(AgentVoicePrintEntity::getId, voicePrintId)
                        .eq(AgentVoicePrintEntity::getCreator, userId));
                if (row != 1) {
                    status.setRollbackOnly(); // 标记事务回滚
                    return false;
                }

                return true;
            } catch (Exception e) {
                status.setRollbackOnly(); // 标记事务回滚
                log.error("删除声纹存在错误原因：{}", e.getMessage());
                throw new RenException("删除声纹出现了错误");
            }
        }));
        // 数据库声纹数据删除成功才继续执行删除声纹服务的数据
        if(b){
            taskExecutor.execute(()-> {
                try {
                    cancelVoicePrint(voicePrintId);
                }catch (RuntimeException e) {
                    log.error("删除声纹存在运行时错误原因：{}，id：{}", e.getMessage(),voicePrintId);
                }
            });
        }
        return b;
    }

    @Override
    public List<AgentVoicePrintVO> list(Long userId, String agentId) {
        // 按照指定当前登录用户和智能体查找数据
        List<AgentVoicePrintEntity> list = baseMapper.selectList(new LambdaQueryWrapper<AgentVoicePrintEntity>()
                .eq(AgentVoicePrintEntity::getAgentId, agentId)
                .eq(AgentVoicePrintEntity::getCreator, userId));
        return list.stream().map(entity -> {
            // 遍历转换成AgentVoicePrintVO类型
            return ConvertUtils.sourceToTarget(entity, AgentVoicePrintVO.class);
        }).toList();

    }

    @Override
    public boolean update(Long userId, AgentVoicePrintUpdateDTO dto) {
        AgentVoicePrintEntity agentVoicePrintEntity = baseMapper
                .selectOne(new LambdaQueryWrapper<AgentVoicePrintEntity>()
                        .eq(AgentVoicePrintEntity::getId, dto.getId())
                        .eq(AgentVoicePrintEntity::getCreator, userId));
        if (agentVoicePrintEntity == null) {
            return false;
        }
        // 获取音频Id
        String audioId = dto.getAudioId();
        // 获取智能体id
        String agentId = agentVoicePrintEntity.getAgentId();
        ByteArrayResource resource;
        // audioId不等于空，且audioId和之前的保存的音频id不一样，则需要重新获取音频数据生成声纹
        if (!StringUtils.isEmpty(audioId) && !audioId.equals(agentVoicePrintEntity.getAudioId())) {
            resource = getVoicePrintAudioWAV(agentId, audioId);

            // 识别一下此声音是否注册过
            IdentifyVoicePrintResponse response = identifyVoicePrint(agentId, resource);
            // 返回分数高于RECOGNITION说明这个声纹已经有了
            if (response != null && response.getScore() > RECOGNITION) {
                // 判断返回的id如果不是要修改的声纹id，说明这个声纹id，现在要注册的声音已经存在且不是原来的声纹，不允许修改
                if (!response.getSpeakerId().equals(dto.getId())) {
                    // 根据识别出的声纹ID查询对应的用户信息
                    AgentVoicePrintEntity existingVoicePrint = baseMapper.selectById(response.getSpeakerId());
                    String existingUserName = existingVoicePrint != null ? existingVoicePrint.getSourceName() : "未知用户";
                    throw new RenException("此次修改不允许，此声音已经注册为声纹了（" + existingUserName + "）");
                }
            }
        } else {
            resource = null;
        }
        // 开启事务
        return Boolean.TRUE.equals(transactionTemplate.execute(status -> {
            try {
                AgentVoicePrintEntity entity = ConvertUtils.sourceToTarget(dto, AgentVoicePrintEntity.class);
                int row = baseMapper.updateById(entity);
                if (row != 1) {
                    status.setRollbackOnly(); // 标记事务回滚
                    return false;
                }
                if (resource != null) {
                    String id = entity.getId();
                    // 先注销之前这个声纹id上的声纹向量
                    cancelVoicePrint(id);
                    // 发送注册声纹请求
                    registerVoicePrint(id, resource);
                }
                return true;
            } catch (RenException e) {
                status.setRollbackOnly(); // 标记事务回滚
                throw e;
            } catch (Exception e) {
                status.setRollbackOnly(); // 标记事务回滚
                log.error("修改声纹错误原因：{}", e.getMessage());
                throw new RenException("修改声纹错误，请联系管理员");
            }
        }));
    }

    /**
     * 获取生纹接口URI对象
     *
     * @return URI对象
     */
    private URI getVoicePrintURI() {
        // 获取声纹接口地址
        String voicePrint = sysParamsService.getValue(Constant.SERVER_VOICE_PRINT, true);
        try {
            return new URI(voicePrint);
        } catch (URISyntaxException e) {
            log.error("路径格式不正确路径：{}，\n错误信息:{}", voicePrint, e.getMessage());
            throw new RuntimeException("声纹接口的地址存在错误，请进入参数管理修改声纹接口地址");
        }
    }

    /**
     * 获取声纹地址基础路径
     * 
     * @param uri 声纹地址uri
     * @return 基础路径
     */
    private String getBaseUrl(URI uri) {
        String protocol = uri.getScheme();
        String host = uri.getHost();
        int port = uri.getPort();
        if (port == -1) {
            return "%s://%s".formatted(protocol, host);
        } else {
            return "%s://%s:%s".formatted(protocol, host, port);
        }
    }

    /**
     * 获取验证Authorization
     *
     * @param uri 声纹地址uri
     * @return Authorization值
     */
    private String getAuthorization(URI uri) {
        // 获取参数
        String query = uri.getQuery();
        // 获取aes加密密钥
        String str = "key=";
        return "Bearer " + query.substring(query.indexOf(str) + str.length());
    }

    /**
     * 获取声纹音频资源数据
     *
     * @param audioId 音频Id
     * @return 声纹音频资源数据
     */
    private ByteArrayResource getVoicePrintAudioWAV(String agentId, String audioId) {
        // 判断这个音频是否属于当前智能体
        boolean b = agentChatHistoryService.isAudioOwnedByAgent(audioId, agentId);
        if (!b) {
            throw new RenException("音频数据不属于这个智能体");
        }
        // 获取到音频数据
        byte[] audio = agentChatAudioService.getAudio(audioId);
        // 如果音频数据为空的直接报错不进行下去
        if (audio == null || audio.length == 0) {
            throw new RenException("音频数据是空的请检查上传数据");
        }
        // 将字节数组包装为资源，返回
        return new ByteArrayResource(audio) {
            @Override
            public String getFilename() {
                return "VoicePrint.WAV"; // 设置文件名
            }
        };
    }

    /**
     * 发送注册声纹http请求
     * 
     * @param id       声纹id
     * @param resource 声纹音频资源
     */
    private void registerVoicePrint(String id, ByteArrayResource resource) {
        // 处理声纹接口地址，获取前缀
        URI uri = getVoicePrintURI();
        String baseUrl = getBaseUrl(uri);
        String requestUrl = baseUrl + "/voiceprint/register";
        // 创建请求体
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("speaker_id", id);
        body.add("file", resource);

        // 创建请求头
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", getAuthorization(uri));
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        // 创建请求体
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        // 发送 POST 请求
        ResponseEntity<String> response = restTemplate.postForEntity(requestUrl, requestEntity, String.class);

        if (response.getStatusCode() != HttpStatus.OK) {
            log.error("声纹注册失败,请求路径：{}", requestUrl);
            throw new RenException("声纹保存失败,请求不成功");
        }
        // 检查响应内容
        String responseBody = response.getBody();
        if (responseBody == null || !responseBody.contains("true")) {
            log.error("声纹注册失败,请求处理失败内容：{}", responseBody == null ? "空内容" : responseBody);
            throw new RenException("声纹保存失败,请求处理失败");
        }
    }

    /**
     * 发送注销声纹的请求
     * 
     * @param voicePrintId 声纹id
     */
    private void cancelVoicePrint(String voicePrintId) {
        URI uri = getVoicePrintURI();
        String baseUrl = getBaseUrl(uri);
        String requestUrl = baseUrl + "/voiceprint/" + voicePrintId;
        // 创建请求头
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", getAuthorization(uri));
        // 创建请求体
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(headers);

        // 发送 POST 请求
        ResponseEntity<String> response = restTemplate.exchange(requestUrl, HttpMethod.DELETE, requestEntity,
                String.class);
        if (response.getStatusCode() != HttpStatus.OK) {
            log.error("声纹注销失败,请求路径：{}", requestUrl);
            throw new RenException("声纹注销失败,请求不成功");
        }
        // 检查响应内容
        String responseBody = response.getBody();
        if (responseBody == null || !responseBody.contains("true")) {
            log.error("声纹注销失败,请求处理失败内容：{}", responseBody == null ? "空内容" : responseBody);
            throw new RenException("声纹注销失败,请求处理失败");
        }
    }

    /**
     * 发送识别声纹http请求
     * 
     * @param agentId  智能体id
     * @param resource 声纹音频资源
     * @return 返回识别数据
     */
    private IdentifyVoicePrintResponse identifyVoicePrint(String agentId, ByteArrayResource resource) {

        // 获取该智能体所有注册的声纹
        List<AgentVoicePrintEntity> agentVoicePrintList = baseMapper
                .selectList(new LambdaQueryWrapper<AgentVoicePrintEntity>()
                        .select(AgentVoicePrintEntity::getId)
                        .eq(AgentVoicePrintEntity::getAgentId, agentId));

        // 声纹数量为0，说明还没注册过声纹不需要发生识别请求
        if (agentVoicePrintList.isEmpty()) {
            return null;
        }
        // 处理声纹接口地址，获取前缀
        URI uri = getVoicePrintURI();
        String baseUrl = getBaseUrl(uri);
        String requestUrl = baseUrl + "/voiceprint/identify";
        // 创建请求体
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();

        // 创建speaker_id参数
        String speakerIds = agentVoicePrintList.stream()
                .map(AgentVoicePrintEntity::getId)
                .collect(Collectors.joining(","));
        body.add("speaker_ids", speakerIds);
        body.add("file", resource);

        // 创建请求头
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", getAuthorization(uri));
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        // 创建请求体
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        // 发送 POST 请求
        ResponseEntity<String> response = restTemplate.postForEntity(requestUrl, requestEntity, String.class);

        if (response.getStatusCode() != HttpStatus.OK) {
            log.error("声纹识别请求失败,请求路径：{}", requestUrl);
            throw new RenException("声纹识别失败,请求不成功");
        }
        // 检查响应内容
        String responseBody = response.getBody();
        if (responseBody != null) {
            return JsonUtils.parseObject(responseBody, IdentifyVoicePrintResponse.class);
        }
        return null;
    }
}
