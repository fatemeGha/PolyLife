import {
  Inbox,
  MessageCircle,
  RefreshCw,
  Send,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Avatar, EmptyState, ErrorNotice, Loading } from "./UI";

const date = new Intl.DateTimeFormat("fa-IR", {
  hour: "2-digit",
  minute: "2-digit",
  month: "short",
  day: "numeric",
});

export default function Messages({ initialUserId, notify }) {
  const [threads, setThreads] = useState([]);
  const [activeUserId, setActiveUserId] = useState(initialUserId || null);
  const [thread, setThread] = useState(null);
  const [loading, setLoading] = useState(true);
  const [threadLoading, setThreadLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  const loadThreads = async () => {
    try {
      const payload = await api.messageThreads();
      setThreads(payload);
      if (!activeUserId && payload.length) setActiveUserId(payload[0].profile.user_id);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  };

  const loadThread = async (userId, quiet = false) => {
    if (!userId) return;
    if (!quiet) setThreadLoading(true);
    try {
      const payload = await api.messageThread(userId);
      setThread(payload);
      setThreads((items) =>
        items.map((item) =>
          item.profile.user_id === Number(userId)
            ? { ...item, unread_count: 0 }
            : item,
        ),
      );
      window.setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 60);
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setThreadLoading(false);
    }
  };

  useEffect(() => {
    setActiveUserId(initialUserId || null);
    loadThreads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialUserId]);

  useEffect(() => {
    if (activeUserId) loadThread(activeUserId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeUserId]);

  const submit = async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const input = new FormData(form).get("message")?.toString().trim();
    if (!input || !activeUserId) return;
    setSending(true);
    try {
      const message = await api.sendMessage(activeUserId, input);
      setThread((value) => ({
        ...value,
        messages: [...(value?.messages || []), message],
      }));
      form.reset();
      await loadThreads();
      window.setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 60);
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setSending(false);
    }
  };

  if (error) return <ErrorNotice message={error} retry={loadThreads} />;
  if (loading) return <Loading label="گفتگوها را دریافت می‌کنیم…" />;

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Direct · گفتگوی خصوصی</span>
          <h1>پیام‌های مستقیم</h1>
          <p>با ورزشکاران، مربیان و متخصصان در یک فضای خصوصی گفتگو کن.</p>
        </div>
        <span className="heading-icon">
          <MessageCircle size={28} />
        </span>
      </div>

      <div className="messages-layout card">
        <aside className="thread-list">
          <div className="thread-list__heading">
            <strong>گفتگوها</strong>
            <button
              type="button"
              className="icon-button"
              onClick={loadThreads}
              aria-label="تازه‌سازی گفتگوها"
            >
              <RefreshCw size={17} />
            </button>
          </div>
          {threads.length ? (
            threads.map((item) => (
              <button
                type="button"
                key={item.profile.user_id}
                className={
                  Number(activeUserId) === item.profile.user_id
                    ? "thread-item thread-item--active"
                    : "thread-item"
                }
                onClick={() => setActiveUserId(item.profile.user_id)}
              >
                <Avatar profile={item.profile} />
                <span>
                  <strong>{item.profile.display_name || item.profile.username}</strong>
                  <small>{item.last_message.body}</small>
                </span>
                {item.unread_count > 0 && (
                  <b>{item.unread_count.toLocaleString("fa-IR")}</b>
                )}
              </button>
            ))
          ) : (
            <div className="thread-list__empty">
              <Inbox size={24} />
              <span>از پروفایل یک کاربر، گفتگوی تازه را شروع کن.</span>
            </div>
          )}
        </aside>

        <div className="chat-panel">
          {!activeUserId ? (
            <EmptyState
              icon={MessageCircle}
              title="یک گفتگو انتخاب کن"
              description="برای شروع، در بخش کشف کاربران روی دکمه پیام بزن."
            />
          ) : threadLoading ? (
            <Loading label="پیام‌ها را باز می‌کنیم…" />
          ) : thread ? (
            <>
              <header className="chat-panel__header">
                <Avatar profile={thread.profile} />
                <span>
                  <strong>{thread.profile.display_name || thread.profile.username}</strong>
                  <small>@{thread.profile.username}</small>
                </span>
              </header>
              <div className="message-stream">
                {thread.messages.length ? (
                  thread.messages.map((message) => (
                    <div
                      className={message.mine ? "message-bubble message-bubble--mine" : "message-bubble"}
                      key={message.id}
                    >
                      <p>{message.body}</p>
                      <small>
                        {date.format(new Date(message.created_at))}
                        {message.mine && message.is_read ? " · دیده شد" : ""}
                      </small>
                    </div>
                  ))
                ) : (
                  <div className="chat-empty">
                    <MessageCircle size={25} />
                    <span>اولین پیام این گفتگو را بنویس.</span>
                  </div>
                )}
                <div ref={endRef} />
              </div>
              <form className="message-composer" onSubmit={submit}>
                <label className="sr-only" htmlFor="direct-message">
                  متن پیام
                </label>
                <textarea
                  id="direct-message"
                  name="message"
                  rows="2"
                  maxLength={3000}
                  placeholder="پیامت را بنویس…"
                  required
                />
                <button
                  type="submit"
                  className="button button--primary"
                  disabled={sending}
                >
                  <Send size={18} />
                  {sending ? "در حال ارسال…" : "ارسال"}
                </button>
              </form>
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}
