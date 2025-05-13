<template>
    <el-dialog :title="'与' + agentName + '的聊天记录' + (currentMacAddress ? '[' + currentMacAddress + ']' : '')"
        :visible.sync="dialogVisible" width="80%" :before-close="handleClose" custom-class="chat-history-dialog">
        <div class="chat-container">
            <div class="session-list" @scroll="handleScroll">
                <div v-for="session in sessions" :key="session.sessionId" class="session-item"
                    :class="{ active: currentSessionId === session.sessionId }" @click="selectSession(session)">
                    <img :src="getUserAvatar(session.sessionId)" class="avatar" />
                    <div class="session-info">
                        <div class="session-time">{{ formatTime(session.createdAt) }}</div>
                        <div class="message-count">{{ session.chatCount > 99 ? '99' : session.chatCount }}</div>
                    </div>
                </div>
                <div v-if="loading" class="loading">加载中...</div>
                <div v-if="!hasMore" class="no-more">没有更多记录了</div>
            </div>
            <div class="chat-content">
                <div v-if="currentSessionId" class="messages">
                    <div v-for="(message, index) in messagesWithTime" :key="message.id">
                        <div v-if="message.type === 'time'" class="time-divider">
                            {{ message.content }}
                        </div>
                        <div v-else class="message-item" :class="{ 'user-message': message.chatType === 1 }">
                            <img :src="message.chatType === 1 ? getUserAvatar(currentSessionId) : require('@/assets/xiaozhi-logo.png')"
                                class="avatar" />
                            <div class="message-content">
                                {{ message.content }}
                                <i v-if="message.audioId" :class="getAudioIconClass(message)"
                                    @click="playAudio(message)" class="audio-icon"></i>
                            </div>
                        </div>
                    </div>
                </div>
                <div v-else class="no-session-selected">
                    请选择会话查看聊天记录
                </div>
            </div>
        </div>
    </el-dialog>
</template>

<script>
import Api from '@/apis/api';

export default {
    name: 'ChatHistoryDialog',
    props: {
        visible: {
            type: Boolean,
            default: false
        },
        agentId: {
            type: String,
            required: true
        },
        agentName: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            dialogVisible: false,
            sessions: [],
            messages: [],
            currentSessionId: '',
            currentMacAddress: '',
            page: 1,
            limit: 20,
            loading: false,
            hasMore: true,
            scrollTimer: null,
            isFirstLoad: true,
            playingAudioId: null,
            audioElement: null
        };
    },
    watch: {
        visible(val) {
            this.dialogVisible = val;
            if (val) {
                this.resetData();
                this.loadSessions();
            }
        },
        dialogVisible(val) {
            if (!val) {
                this.$emit('update:visible', false);
            }
        }
    },
    computed: {
        messagesWithTime() {
            if (!this.messages || this.messages.length === 0) return [];

            const result = [];
            const TIME_INTERVAL = 60 * 1000; // 1分钟的时间间隔（毫秒）

            // 添加第一条消息的时间标记
            if (this.messages[0]) {
                result.push({
                    type: 'time',
                    content: this.formatTime(this.messages[0].createdAt),
                    id: `time-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
                });
            }

            // 处理消息列表
            for (let i = 0; i < this.messages.length; i++) {
                const currentMessage = this.messages[i];
                result.push(currentMessage);

                // 检查是否需要添加时间标记
                if (i < this.messages.length - 1) {
                    const currentTime = new Date(currentMessage.createdAt).getTime();
                    const nextTime = new Date(this.messages[i + 1].createdAt).getTime();

                    if (nextTime - currentTime > TIME_INTERVAL) {
                        result.push({
                            type: 'time',
                            content: this.formatTime(this.messages[i + 1].createdAt),
                            id: `time-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
                        });
                    }
                }
            }

            return result;
        }
    },
    methods: {
        resetData() {
            this.sessions = [];
            this.messages = [];
            this.currentSessionId = '';
            this.currentMacAddress = '';
            this.page = 1;
            this.loading = false;
            this.hasMore = true;
            this.isFirstLoad = true;
        },
        handleClose() {
            this.dialogVisible = false;
        },
        loadSessions() {
            if (this.loading || (!this.isFirstLoad && !this.hasMore)) {
                return;
            }

            this.loading = true;
            const params = {
                page: this.page,
                limit: this.limit
            };

            Api.agent.getAgentSessions(this.agentId, params, (res) => {
                if (res.data && res.data.data && Array.isArray(res.data.data.list)) {
                    const list = res.data.data.list;
                    this.hasMore = list.length === this.limit;

                    this.sessions = [...this.sessions, ...list];
                    this.page++;

                    if (this.sessions.length > 0 && !this.currentSessionId) {
                        this.selectSession(this.sessions[0]);
                    }
                }
                this.loading = false;
                this.isFirstLoad = false;
            });
        },
        selectSession(session) {
            this.currentSessionId = session.sessionId;
            Api.agent.getAgentChatHistory(this.agentId, session.sessionId, (res) => {
                if (res.data && res.data.data) {
                    this.messages = res.data.data;
                    if (this.messages.length > 0 && this.messages[0].macAddress) {
                        this.currentMacAddress = this.messages[0].macAddress;
                    }
                }
            });
        },
        handleScroll(e) {
            if (this.scrollTimer) {
                clearTimeout(this.scrollTimer);
            }

            this.scrollTimer = setTimeout(() => {
                const { scrollTop, scrollHeight, clientHeight } = e.target;
                // 当滚动到底部时加载更多
                if (scrollHeight - scrollTop <= clientHeight + 50) {
                    this.loadSessions();
                }
            }, 200);
        },
        formatTime(timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);

            const hours = date.getHours().toString().padStart(2, '0');
            const minutes = date.getMinutes().toString().padStart(2, '0');

            if (date >= today) {
                return `今天 ${hours}:${minutes}`;
            } else if (date >= yesterday) {
                return `昨天 ${hours}:${minutes}`;
            } else {
                const year = date.getFullYear();
                const month = (date.getMonth() + 1).toString().padStart(2, '0');
                const day = date.getDate().toString().padStart(2, '0');
                return `${year}-${month}-${day} ${hours}:${minutes}`;
            }
        },
        getAudioIconClass(message) {
            if (this.playingAudioId === message.audioId) {
                return 'el-icon-loading';
            }
            return 'el-icon-video-play';
        },
        playAudio(message) {
            if (this.playingAudioId === message.audioId) {
                // 如果正在播放当前音频，则停止播放
                if (this.audioElement) {
                    this.audioElement.pause();
                    this.audioElement = null;
                }
                this.playingAudioId = null;
                return;
            }

            // 停止当前正在播放的音频
            if (this.audioElement) {
                this.audioElement.pause();
                this.audioElement = null;
            }

            // 先获取音频下载ID
            this.playingAudioId = message.audioId;
            Api.agent.getAudioId(message.audioId, (res) => {
                if (res.data && res.data.data) {
                    // 使用获取到的下载ID播放音频
                    this.audioElement = new Audio(Api.getServiceUrl() + `/agent/play/${res.data.data}`);

                    this.audioElement.onended = () => {
                        this.playingAudioId = null;
                        this.audioElement = null;
                    };

                    this.audioElement.play();
                }
            });
        },
        getUserAvatar(sessionId) {
            // 从 sessionId 中提取所有数字
            const numbers = sessionId.match(/\d+/g);
            if (!numbers) return require('@/assets/user-avatar1.png');

            // 将所有数字相加
            const sum = numbers.reduce((acc, num) => acc + parseInt(num), 0);

            // 计算模5并加1，得到1-5之间的数字
            const avatarIndex = (sum % 5) + 1;

            // 返回对应的头像图片
            return require(`@/assets/user-avatar${avatarIndex}.png`);
        }
    }
};
</script>

<style scoped>
.chat-container {
    display: flex;
    height: 100%;
}

.session-list {
    width: 250px;
    border-right: 1px solid #eee;
    overflow-y: auto;
    padding: 10px;
}

.session-item {
    display: flex;
    align-items: center;
    padding: 10px;
    cursor: pointer;
    border-radius: 8px;
    margin-bottom: 10px;
}

.session-item:hover {
    background-color: #f5f5f5;
}

.session-item.active {
    background-color: #e6f7ff;
}

.avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    margin-right: 10px;
}

.session-info {
    flex: 1;
}

.session-time {
    font-size: 14px;
    color: #272727;
    float: left;
    height: 30px;
    line-height: 30px;
    width: calc(100% - 30px);
    /* 为消息数量留出空间 */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.message-count {
    font-size: 14px;
    color: #fff;
    background-color: #b4b4b4;
    border-radius: 20px;
    float: left;
    width: 20px;
    height: 20px;
    line-height: 20px;
    margin-top: 5px;
    margin-left: 5px;
}

.chat-content {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
}

.message-item {
    display: flex;
    margin-bottom: 20px;
}

.message-item.user-message {
    flex-direction: row-reverse;
}

.message-content {
    max-width: 60%;
    padding: 10px 15px;
    border-radius: 8px;
    background-color: #f0f0f0;
    margin: 0 10px;
    text-align: left;
    line-height: 20px;
    position: relative;
    display: flex;
    align-items: center;
}

.audio-icon {
    font-size: 20px;
    cursor: pointer;
    margin: 0 5px;
    color: #1890ff;
}

.user-message .message-content {
    background-color: #1890ff;
    color: white;
    flex-direction: row-reverse;
}

.user-message .audio-icon {
    color: white;
}

.loading,
.no-more {
    text-align: center;
    padding: 10px 10px 30px 10px;
    color: #999;
}

.no-session-selected {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    color: #999;
}

.time-divider {
    text-align: center;
    margin: 10px 0;
    color: #999;
    font-size: 12px;
}

.time-divider::before,
.time-divider::after {
    content: '';
    display: inline-block;
    width: 30%;
    height: 1px;
    background-color: #eee;
    vertical-align: middle;
    margin: 0 10px;
}
</style>

<style>
.chat-history-dialog {
    display: flex;
    flex-direction: column;
    min-width: 700px;
    margin: 0 !important;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    height: 90vh;
    max-width: 85vw;
    border-radius: 12px;
    overflow: hidden;
}

.chat-history-dialog .el-dialog__header {
    background-color: #e6f7ff;
    padding: 15px 20px;
}

.chat-history-dialog .el-dialog__body {
    padding: 0;
    overflow: hidden;
    height: calc(90vh - 54px);
    /* 减去标题栏的高度 */
}
</style>