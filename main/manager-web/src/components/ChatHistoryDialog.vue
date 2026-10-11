<template>
    <el-dialog :title="$t('chatHistory.with') + agentName + (currentMacAddress ? '[' + currentMacAddress + ']' : '')"
        :visible.sync="dialogVisible" width="80%" :before-close="handleClose" custom-class="chat-history-dialog">
        <template slot="title">
            <span style="font-size: 18px;">
                {{ $t('chatHistory.with') + agentName + $t('chatHistory.dialogTitle') }}
                <template v-if="currentMacAddress">
                    [<MacAddressMask :macAddress="currentMacAddress" />]
                </template>
            </span>
        </template>
        <div class="chat-container">
            <div class="session-list" @scroll="handleScroll">
                <div class="session-list-header">
                    <span class="session-count">{{ $t('chatHistory.sessionCount', { count: sessions.length }) }}</span>
                    <el-button 
                        v-if="sessions.length > 0"
                        type="text" 
                        size="mini" 
                        class="delete-all-btn"
                        @click="deleteAllSessions"
                        :title="$t('chatHistory.deleteAllSessions')">
                        {{ $t('chatHistory.deleteAll') }}
                    </el-button>
                </div>
                <div v-for="session in sessions" :key="session.sessionId" class="session-item"
                    :class="{ active: currentSessionId === session.sessionId }" @click="selectSession(session)">
                    <img :src="getUserAvatar(session.sessionId)" class="avatar" />
                    <div class="session-info">
                        <div class="session-time">{{ session.title || formatTime(session.createdAt) }}</div>
                        <div class="message-count">{{ session.chatCount > 99 ? '99' : session.chatCount }}</div>
                    </div>
                    <div class="session-actions">
                        <el-button 
                            type="text" 
                            icon="el-icon-delete" 
                            size="mini" 
                            class="delete-btn"
                            @click.stop="deleteSession(session)"
                            :title="$t('chatHistory.deleteSession')">
                        </el-button>
                    </div>
                </div>
                <div v-if="loading" class="loading">{{ $t('chatHistory.loading') }}</div>
                <div v-if="!hasMore" class="no-more">{{ $t('chatHistory.noMoreRecords') }}</div>
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
                                {{ extractContentFromString(message.content) }}
                                <i v-if="message.audioId" :class="getAudioIconClass(message)"
                                    @click="playAudio(message)" class="audio-icon"></i>
                            </div>
                        </div>
                    </div>
                </div>
                <div v-else class="no-session-selected">
                    {{ $t('chatHistory.selectSession') }}
                </div>
            </div>
        </div>
    </el-dialog>
</template>

<script>
import Api from '@/apis/api';
import CustomDialog from '@/components/CustomDialog.vue';
import MacAddressMask from '@/components/MacAddressMask.vue';

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
    components: {
        CustomDialog,
        MacAddressMask,
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
            const TIME_INTERVAL = 60 * 1000; // 1 minute time interval (milliseconds)

            // Add time marker for first message
            if (this.messages[0]) {
                result.push({
                    type: 'time',
                    content: this.formatTime(this.messages[this.messages.length - 1].createdAt),
                    id: `time-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
                });
            }

            // Process message list
            for (let i = 0; i < this.messages.length; i++) {
                const currentMessage = this.messages[i];
                result.push(currentMessage);

                // Check if time marker needs to be added
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
        /**
         * Extract chat content from content field
         * If content is JSON format (like {"speaker": "Unknown Speaker", "content": "What time is it?"}), extract content field
         * If content is plain string, return directly
         * 
         * @param {string} content Original content
         * @returns {string} Extracted chat content
         */
        extractContentFromString(content) {
            if (!content || content.trim() === '') {
                return content;
            }

            // Try to parse as JSON
            try {
                const jsonObj = JSON.parse(content);
                if (jsonObj && typeof jsonObj === 'object' && jsonObj.content) {
                    return jsonObj.content;
                }
            } catch (e) {
                // If not valid JSON, return original content directly
            }

            // If not JSON format or no content field, return original content directly
            return content;
        },
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
                    // 更新会话列表中的聊天记录数量
                    this.sessions = this.sessions.map(item => {
                        if (item.sessionId === session.sessionId) {
                            item.chatCount = this.messages.length;
                        }
                        return item;
                    })
                }
            });
        },
        handleScroll(e) {
            if (this.scrollTimer) {
                clearTimeout(this.scrollTimer);
            }

            this.scrollTimer = setTimeout(() => {
                const { scrollTop, scrollHeight, clientHeight } = e.target;
                // Load more when scrolling to bottom
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
                return `${this.$t('chatHistory.today')} ${hours}:${minutes}`;
            } else if (date >= yesterday) {
                return `${this.$t('chatHistory.yesterday')} ${hours}:${minutes}`;
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
                // If currently playing this audio, stop playback
                if (this.audioElement) {
                    this.audioElement.pause();
                    this.audioElement = null;
                }
                this.playingAudioId = null;
                return;
            }

            // Stop currently playing audio
            if (this.audioElement) {
                this.audioElement.pause();
                this.audioElement = null;
            }

            // First get audio download ID
            this.playingAudioId = message.audioId;
            Api.agent.getAudioId(message.audioId, (res) => {
                if (res.data && res.data.data) {
                    // Use the obtained download ID to play audio
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
            // Extract all numbers from sessionId
            const numbers = sessionId.match(/\d+/g);
            if (!numbers) return require('@/assets/user-avatar1.png');

            // Sum all numbers
            const sum = numbers.reduce((acc, num) => acc + parseInt(num), 0);

            // Calculate modulo 5 and add 1 to get number between 1-5
            const avatarIndex = (sum % 5) + 1;

            // Return corresponding avatar image
            return require(`@/assets/user-avatar${avatarIndex}.png`);
        },
        deleteSession(session) {
            this.$confirm(this.$t('chatHistory.deleteConfirm'), this.$t('common.warning'), {
                confirmButtonText: this.$t('common.confirm'),
                cancelButtonText: this.$t('common.cancel'),
                type: 'warning'
            }).then(() => {
                Api.agent.deleteAgentChatSession(this.agentId, session.sessionId, (res) => {
                    if (res.data && res.data.code === 0) {
                        this.$message.success(this.$t('chatHistory.deleteSuccess'));
                        
                        // Remove session from list
                        const index = this.sessions.findIndex(s => s.sessionId === session.sessionId);
                        if (index > -1) {
                            this.sessions.splice(index, 1);
                        }
                        
                        // If deleted session was currently selected, clear selection
                        if (this.currentSessionId === session.sessionId) {
                            this.currentSessionId = '';
                            this.messages = [];
                            this.currentMacAddress = '';
                        }
                        
                        // If no sessions left, reload the list
                        if (this.sessions.length === 0) {
                            this.resetData();
                            this.loadSessions();
                        }
                    } else {
                        this.$message.error(this.$t('chatHistory.deleteFailed'));
                    }
                });
            }).catch(() => {
                // User cancelled deletion
            });
        },
        deleteAllSessions() {
            this.$confirm(this.$t('chatHistory.deleteAllConfirm'), this.$t('common.warning'), {
                confirmButtonText: this.$t('common.confirm'),
                cancelButtonText: this.$t('common.cancel'),
                type: 'warning'
            }).then(() => {
                // Delete all sessions by calling the existing deleteByAgentId method
                Api.agent.deleteAllAgentChatSessions(this.agentId, (res) => {
                    if (res.data && res.data.code === 0) {
                        this.$message.success(this.$t('chatHistory.deleteAllSuccess'));
                        
                        // Clear all data
                        this.resetData();
                        this.loadSessions();
                    } else {
                        this.$message.error(this.$t('chatHistory.deleteAllFailed'));
                    }
                });
            }).catch(() => {
                // User cancelled deletion
            });
        }
    }
};
</script>

<style scoped>
.chat-container {
    display: flex;
    flex: 1;
    min-height: 0;
}

.session-list {
    width: 250px;
    border-right: 1px solid #eee;
    overflow-y: auto;
    padding: 10px;
}

.session-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #eee;
    margin-bottom: 10px;
}

.session-count {
    font-size: 12px;
    color: #666;
    font-weight: 500;
}

.delete-all-btn {
    color: #f56c6c;
    font-size: 12px;
    padding: 4px 8px;
}

.delete-all-btn:hover {
    color: #f56c6c;
    background-color: #fef0f0;
}

.session-item {
    display: flex;
    align-items: center;
    padding: 10px;
    cursor: pointer;
    border-radius: 8px;
    margin-bottom: 10px;
    position: relative;
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
    width: calc(100% - 50px);
}

.session-actions {
    opacity: 0;
    transition: opacity 0.2s;
    margin-left: 10px;
}

.session-item:hover .session-actions {
    opacity: 1;
}

.delete-btn {
    color: #f56c6c;
    padding: 4px;
}

.delete-btn:hover {
    color: #f56c6c;
    background-color: #fef0f0;
}

.session-time {
    font-size: 14px;
    color: #272727;
    float: left;
    height: 30px;
    line-height: 30px;
    width: calc(100% - 30px);
    /* Leave space for message count */
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
    min-width: 700px;
    margin: 0 !important;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    height: 90vh;
    max-width: 85vw;
    /* 兜底，防止 size="large" 那个 height 没有生效时弹框缩成内容高度 */
    height: calc(100vh - 20px) !important;
}

.chat-history-dialog .el-dialog__body {
    padding: 0;
    overflow: hidden;
    height: calc(90vh - 54px);
    /* Subtract the height of the title bar */
}
</style>