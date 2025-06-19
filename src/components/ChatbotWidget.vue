<template>
    <div>
        <div
            v-if="open"
            class="chatbot-window"
            :class="{ expanded: isExpanded }"
            :style="isExpanded ? expandedWindowStyle : {}"
        >
            <div
                class="chatbot-header"
                @mousedown="startDrag"
                @touchstart="startDrag"
            >
                <span>Flight Assistant</span>
                <div class="header-buttons">
                    <button
                        class="expand-button"
                        @click.stop="toggleExpand"
                        :title="isExpanded ? 'Collapse' : 'Expand'"
                    >
                        {{ isExpanded ? "−" : "⇱" }}
                    </button>
                    <button
                        class="close-button"
                        @click="toggleOpen"
                        title="Close"
                    >
                        ×
                    </button>
                </div>
            </div>
            <div class="chatbot-messages">
                <div
                    v-for="(msg, i) in messages"
                    :key="i"
                    :class="['chat-message', msg.role]"
                >
                    {{ msg.text }}
                </div>
                <div v-if="isLoading" class="chat-message bot loading">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
            <div class="chatbot-input">
                <div class="input-wrapper">
                    <input
                        v-model="input"
                        @keyup.enter="send"
                        placeholder="Ask me about your flight log..."
                        :disabled="isLoading"
                    />
                    <button
                        class="send-btn"
                        @click="send"
                        :disabled="isLoading || !input.trim()"
                        aria-label="Send"
                    >
                        <svg
                            width="24"
                            height="24"
                            viewBox="0 0 24 24"
                            fill="none"
                        >
                            <path
                                d="M8 12h8M14 8l4 4-4 4"
                                stroke="#fff"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                        </svg>
                    </button>
                </div>
            </div>
            <div v-if="error" class="error-message">{{ error }}</div>
        </div>
        <button
            v-else
            class="chatbot-fab"
            @click="toggleOpen"
            :style="isExpanded ? expandedFabStyle : {}"
        >
            💬
        </button>
    </div>
</template>

<script>
import { v4 as uuidv4 } from 'uuid'
import { store } from './Globals'

export default {
    data () {
        return {
            open: false,
            isExpanded: false,
            input: '',
            messages: [
                {
                    role: 'bot',
                    text: 'Hi! Ask me anything about your log file.'
                }
            ],
            dragging: false,
            dragOffset: { x: 0, y: 0 },
            position: { x: null, y: null },
            sessionId: uuidv4(),
            isLoading: false,
            error: null
        }
    },
    methods: {
        toggleOpen () {
            this.open = !this.open
            if (!this.open) {
                this.isExpanded = false
                this.position = { x: null, y: null }
            }
        },
        toggleExpand () {
            this.isExpanded = !this.isExpanded
            if (!this.isExpanded) {
                this.position = { x: null, y: null }
            }
        },
        async send () {
            if (!this.input.trim()) return
            const userMessage = this.input
            this.messages.push({ role: 'user', text: userMessage })
            this.input = ''
            this.isLoading = true
            this.error = null
            let binPath = null
            if (store.uploadedBinFilePath && store.logType === 'bin') {
                binPath = store.uploadedBinFilePath
            }
            console.log('Sending binPath to backend:', binPath)
            try {
                const response = await fetch('http://localhost:8000/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        sessionId: this.sessionId,
                        message: userMessage,
                        binPath: binPath
                    })
                })

                if (!response.ok) {
                    throw new Error('Failed to get response from server')
                }

                const data = await response.json()
                if (data.error) {
                    this.messages.push({ role: 'bot', text: data.error })
                } else {
                    this.messages.push({ role: 'bot', text: data.response })
                }
            } catch (err) {
                this.error = err.message
                this.messages.push({
                    role: 'bot',
                    text: 'Sorry, I encountered an error. Please try again.'
                })
            } finally {
                this.isLoading = false
            }
        },
        startDrag (e) {
            if (!this.isExpanded) return
            this.dragging = true
            const event = e.type.startsWith('touch') ? e.touches[0] : e
            const rect = e.currentTarget.parentElement.getBoundingClientRect()
            this.dragOffset = {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top
            }
            document.addEventListener('mousemove', this.onDrag)
            document.addEventListener('mouseup', this.stopDrag)
            document.addEventListener('touchmove', this.onDrag)
            document.addEventListener('touchend', this.stopDrag)
        },
        onDrag (e) {
            if (!this.dragging) return
            const event = e.type.startsWith('touch') ? e.touches[0] : e
            const x = event.clientX - this.dragOffset.x
            const y = event.clientY - this.dragOffset.y
            this.position = { x, y }
        },
        stopDrag () {
            this.dragging = false
            document.removeEventListener('mousemove', this.onDrag)
            document.removeEventListener('mouseup', this.stopDrag)
            document.removeEventListener('touchmove', this.onDrag)
            document.removeEventListener('touchend', this.stopDrag)
        }
    },
    computed: {
        expandedFabStyle () {
            return {
                bottom: '10vh',
                right: '10vw',
                transition: 'all 0.3s ease'
            }
        },
        expandedWindowStyle () {
            if (!this.isExpanded) return {}
            const width = this.expandedWidth + 'px'
            const height = this.expandedHeight + 'px'
            if (this.position.x !== null && this.position.y !== null) {
                return {
                    width,
                    height,
                    top: this.position.y + 'px',
                    left: this.position.x + 'px',
                    bottom: 'unset',
                    right: 'unset',
                    position: 'fixed',
                    transition: 'all 0.3s ease',
                    zIndex: 1000
                }
            } else {
                return {
                    width,
                    height,
                    top: '10vh',
                    left: '10vw',
                    bottom: 'unset',
                    right: 'unset',
                    position: 'fixed',
                    transition: 'all 0.3s ease',
                    zIndex: 1000
                }
            }
        },
        expandedWidth () {
            return Math.round(window.innerWidth * 0.8)
        },
        expandedHeight () {
            return Math.round(window.innerHeight * 0.8)
        }
    }
}
</script>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap");

:root {
    --chatbot-bg: #f8f9fa;
    --header-color: #adb5bd;
    --user-bubble: #dee2e6;
    --bot-bubble: #e2edf8;
    --bot-bubble-text: #1a1a1a;
    --user-bubble-text: #000;
    --input-border: #adb5bd;
    --send-btn-bg: #1976d2;
    --send-btn-hover: #1565c0;
}

* {
    font-family: "Inter", sans-serif;
}

.chatbot-fab {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #6c757d;
    color: white;
    border: none;
    border-radius: 50%;
    width: 56px;
    height: 56px;
    font-size: 28px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
    cursor: pointer;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
}

.chatbot-window {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 340px;
    height: 440px;
    background: rgba(
        248,
        249,
        250,
        0.85
    ); /* Light gray with slight transparency */
    border-radius: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    display: flex;
    flex-direction: column;
    border: 1px solid #ced4da;
    z-index: 1000;
    backdrop-filter: blur(4px); /* Optional: softens background behind */
}

.chatbot-window.expanded {
    border-radius: 24px;
    box-shadow: 0 8px 64px rgba(0, 0, 0, 0.2);
    cursor: move;
}

.chatbot-header {
    background: var(--header-color);
    padding: 16px;
    border-radius: 20px 20px 0 0;
    font-weight: 600;
    font-size: 1.1rem;
    color: #000;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    user-select: none;
}

.header-buttons button {
    background: transparent;
    border: none;
    font-size: 18px;
    color: #000;
    margin-left: 8px;
    cursor: pointer;
}

.chatbot-messages {
    flex: 1;
    overflow-y: auto;
    padding: 24px 16px 16px 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.chat-message {
    max-width: 75%;
    padding: 14px 20px;
    border-radius: 16px;
    font-size: 15px;
    line-height: 1.5;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
    margin-bottom: 2px;
    word-break: break-word;
    background: #f6f6f6;
}

.chat-message.user {
    align-self: flex-end;
    background: #1976d2;
    color: #fff;
    font-weight: 500;
}

.chat-message.bot {
    align-self: flex-start;
    background: #f6f6f6;
    color: #222;
}

.chat-message.loading {
    opacity: 0.7;
    background: #e2edf8;
}

.chatbot-input {
    padding: 16px;
    border-top: 1px solid var(--input-border);
    background: transparent;
}

.input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
}

.chatbot-input input {
    flex: 1;
    width: 100%;
    padding: 12px 48px 12px 18px; /* right padding for button */
    border: none;
    border-radius: 24px;
    font-size: 16px;
    background: #f3f3f3;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
    outline: none;
    transition: box-shadow 0.2s;
}

.chatbot-input input:focus {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.send-btn {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    width: 36px;
    height: 36px;
    border: none;
    background: #8f4fff;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(143, 79, 255, 0.12);
    cursor: pointer;
    transition: background 0.2s, opacity 0.2s;
    padding: 0;
}

.send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: #8f4fff;
}

.send-btn svg {
    display: block;
}

.error-message {
    color: #dc3545;
    font-size: 14px;
    margin-top: 8px;
    text-align: center;
}

.typing-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 12px;
}

.typing-indicator span {
    width: 8px;
    height: 8px;
    background: var(--bot-bubble-text);
    border-radius: 50%;
    opacity: 0.4;
    animation: typing 1s infinite;
}

.typing-indicator span:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing {
    0%,
    100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-4px);
    }
}
</style>
