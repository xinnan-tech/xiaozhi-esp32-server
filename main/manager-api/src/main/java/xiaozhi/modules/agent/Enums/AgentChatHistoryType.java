package xiaozhi.modules.agent.Enums;


import lombok.Getter;

/**
 * 智能体聊天记录类型
 */
@Getter
public enum AgentChatHistoryType {

    USER((byte) 1),
    AGENT((byte) 2);

    private final byte value;

    AgentChatHistoryType(byte i) {
        this.value = i;
    }

}
