export default class BlockingQueue {
    #items   = [];
    #waiters = [];          // {resolve, reject, min, timer, onTimeout}

    /* 空队列一次性闸门 */
    #emptyPromise = null;
    #emptyResolve = null;

    /* 生产者：把数据塞进去 */
    enqueue(item, ...restItems) {
        if (restItems.length === 0) {
            this.#items.push(item);
        }
        // 如果有额外参数，批量处理所有项
        else {
            const items = [item, ...restItems].filter(i => i);
            if (items.length === 0) return;
            this.#items.push(...items);
        }
        // 若有空队列闸门，一次性放行所有等待者
        if (this.#emptyResolve) {
            this.#emptyResolve();
            this.#emptyResolve = null;
            this.#emptyPromise = null;
        }

        // 唤醒所有正在等的 waiter
        this.#wakeWaiters();
    }

    /* 消费者：min 条或 timeout ms 先到谁 */
    async dequeue(min = 1, timeout = Infinity, onTimeout = null) {
        // 1. 若空，等第一次数据到达（所有调用共享同一个 promise）
        if (this.#items.length === 0) {
            await this.#waitForFirstItem();
        }

        // 立即满足
        if (this.#items.length >= min) {
            return this.#flush();
        }

        // 需要等待
        return new Promise((resolve, reject) => {
            let timer = null;
            const waiter = { resolve, reject, min, onTimeout, timer };

            // 超时逻辑
            if (Number.isFinite(timeout)) {
                waiter.timer = setTimeout(() => {
                    this.#removeWaiter(waiter);
                    if (onTimeout) onTimeout(this.#items.length);
                    resolve(this.#flush());
                }, timeout);
            }

            this.#waiters.push(waiter);
        });
    }

    /* 空队列闸门生成器 */
    #waitForFirstItem() {
        if (!this.#emptyPromise) {
            this.#emptyPromise = new Promise(r => (this.#emptyResolve = r));
        }
        return this.#emptyPromise;
    }

    /* 内部：每次数据变动后，检查哪些 waiter 已满足 */
    #wakeWaiters() {
        for (let i = this.#waiters.length - 1; i >= 0; i--) {
            const w = this.#waiters[i];
            if (this.#items.length >= w.min) {
                this.#removeWaiter(w);
                w.resolve(this.#flush());
            }
        }
    }

    #removeWaiter(waiter) {
        const idx = this.#waiters.indexOf(waiter);
        if (idx !== -1) {
            this.#waiters.splice(idx, 1);
            if (waiter.timer) clearTimeout(waiter.timer);
        }
    }

    #flush() {
        const snapshot = [...this.#items];
        this.#items.length = 0;
        return snapshot;
    }

    /* 当前缓存长度（不含等待者） */
    get length() {
        return this.#items.length;
    }
}