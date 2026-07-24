import {
  Bell,
  BookOpen,
  Heart,
  MessageCircle,
  ReceiptText,
  UserPlus,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { Avatar, EmptyState, ErrorNotice, Loading } from "./UI";

const icons = {
  follow: UserPlus,
  like: Heart,
  comment: MessageCircle,
  message: MessageCircle,
  post: BookOpen,
  course: BookOpen,
  purchase: ReceiptText,
};

const date = new Intl.DateTimeFormat("fa-IR", {
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function contextFor(item) {
  if (item.target_page === "feed") return { postId: item.target_id };
  if (item.target_page === "member") return { profileId: Number(item.target_id) };
  if (item.target_page === "messages") return { userId: Number(item.target_id) };
  if (item.target_page === "courses") return { courseId: item.target_id };
  return null;
}

export default function Activity({ onNavigate }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await api.activity("me"));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">ردپای واقعی حساب</span>
          <h1>فعالیت‌ها و اعلان‌ها</h1>
          <p>هر رویداد جزئیات و مقصد واقعی دارد؛ روی آن بزن تا همان پست، دوره یا گفتگو باز شود.</p>
        </div>
        <span className="heading-icon">
          <Bell size={28} />
        </span>
      </div>

      {error && <ErrorNotice message={error} retry={load} />}
      {loading ? (
        <Loading label="فعالیت‌ها را مرتب می‌کنیم…" />
      ) : items.length ? (
        <div className="activity-timeline">
          {items.map((item) => {
            const Icon = icons[item.type] || Bell;
            return (
              <button
                type="button"
                className="card activity-row"
                key={item.id}
                onClick={() => onNavigate(item.target_page, contextFor(item))}
              >
                {item.actor ? (
                  <Avatar profile={item.actor} />
                ) : (
                  <span className={`activity-row__icon activity-row__icon--${item.type}`}>
                    <Icon size={20} />
                  </span>
                )}
                <span className="activity-row__body">
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                  <small>{date.format(new Date(item.created_at))}</small>
                </span>
                <span className="activity-row__open">باز کردن</span>
              </button>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={Bell}
          title="فعالیتی ثبت نشده"
          description="تعامل‌ها، پیام‌ها، خریدها و پیشرفت آموزشی اینجا ثبت می‌شوند."
        />
      )}
    </section>
  );
}
