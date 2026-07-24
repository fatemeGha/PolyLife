import {
  BarChart3,
  Clock3,
  Dumbbell,
  Heart,
  ImagePlus,
  MessageCircle,
  MoreHorizontal,
  Repeat2,
  Send,
  Sparkles,
  Weight,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, results } from "../api";
import { Avatar, EmptyState, ErrorNotice, Loading } from "./UI";

const number = new Intl.NumberFormat("fa-IR");
const date = new Intl.DateTimeFormat("fa-IR", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function WorkoutDetails({ workout }) {
  if (!workout) return null;
  return (
    <div className="workout-stats" aria-label="جزئیات رکورد">
      <span>
        <Dumbbell size={17} />
        {workout.exercise_type}
      </span>
      {workout.weight_kg && (
        <span>
          <Weight size={17} />
          {number.format(Number(workout.weight_kg))} کیلو
        </span>
      )}
      {workout.repetitions && (
        <span>
          <Repeat2 size={17} />
          {number.format(workout.repetitions)} تکرار
        </span>
      )}
      {workout.duration_seconds && (
        <span>
          <Clock3 size={17} />
          {number.format(Math.round(workout.duration_seconds / 60))} دقیقه
        </span>
      )}
    </div>
  );
}

function CommentBox({ postId, onCountChange }) {
  const [comments, setComments] = useState([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    api
      .comments(postId)
      .then((payload) => mounted && setComments(payload))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, [postId]);

  const submit = async (event) => {
    event.preventDefault();
    if (!text.trim()) return;
    const comment = await api.addComment(postId, { text: text.trim() });
    setComments((items) => [...items, comment]);
    onCountChange?.(1);
    setText("");
  };

  if (loading) return <Loading label="در حال دریافت گفتگو…" />;
  return (
    <div className="comments">
      {comments.map((comment) => (
        <div className="comment" key={comment.id}>
          <span className="avatar avatar--tiny avatar--fallback">
            {comment.username.slice(0, 2)}
          </span>
          <div>
            <strong>{comment.username}</strong>
            <p>{comment.text}</p>
          </div>
        </div>
      ))}
      <form className="comment-form" onSubmit={submit}>
        <label className="sr-only" htmlFor={`comment-${postId}`}>
          نوشتن دیدگاه
        </label>
        <input
          id={`comment-${postId}`}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="دیدگاه سازنده‌ای بنویسید…"
          maxLength={1500}
        />
        <button type="submit" className="icon-button icon-button--filled" aria-label="ارسال دیدگاه">
          <Send size={17} />
        </button>
      </form>
    </div>
  );
}

export function PostCard({
  post,
  onChanged,
  onError,
  onOpenProfile,
  focused = false,
}) {
  const [liked, setLiked] = useState(post.liked_by_me);
  const [likeCount, setLikeCount] = useState(post.like_count);
  const [commentCount, setCommentCount] = useState(post.comment_count);
  const [showComments, setShowComments] = useState(false);

  const toggleLike = async () => {
    const previous = { liked, likeCount };
    setLiked(!liked);
    setLikeCount((count) => count + (liked ? -1 : 1));
    try {
      const response = await api.like(post.id, liked);
      setLiked(response.liked);
      setLikeCount(response.like_count);
    } catch (error) {
      setLiked(previous.liked);
      setLikeCount(previous.likeCount);
      onError(error.message);
    }
  };

  const report = async () => {
    const reason = window.prompt("دلیل گزارش این پست چیست؟");
    if (!reason?.trim()) return;
    try {
      await api.reportPost(post.id, reason.trim());
      onChanged("گزارش شما برای بررسی ثبت شد.");
    } catch (error) {
      onError(error.message);
    }
  };

  const share = async () => {
    const url = `${window.location.origin}${window.location.pathname}#feed/post/${post.id}`;
    try {
      if (navigator.share) {
        await navigator.share({
          title: `پست ${post.author?.display_name || post.author_username}`,
          text: post.body.slice(0, 140),
          url,
        });
        onChanged("پست برای اشتراک‌گذاری آماده شد.");
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
        onChanged("لینک مستقیم پست کپی شد.");
      } else {
        window.prompt("لینک مستقیم پست", url);
      }
    } catch (error) {
      if (error.name !== "AbortError") onError("اشتراک‌گذاری انجام نشد.");
    }
  };

  return (
    <article
      id={`post-${post.id}`}
      className={focused ? "card post-card post-card--focused" : "card post-card"}
    >
      <header className="post-card__header">
        <button
          type="button"
          className="post-author-button"
          onClick={() => onOpenProfile?.(post.author_id)}
        >
          <Avatar profile={post.author} />
          <span>
            <strong>{post.author?.display_name || post.author_username}</strong>
            <small>
              {post.author?.badge || "عضو جامعه"} · {date.format(new Date(post.created_at))}
            </small>
          </span>
        </button>
        <button type="button" className="icon-button" aria-label="گزارش پست" onClick={report}>
          <MoreHorizontal size={20} />
        </button>
      </header>

      <p className="post-card__body">{post.body}</p>
      <WorkoutDetails workout={post.workout} />
      {post.media_url && (
        <img className="post-card__media" src={post.media_url} alt="تصویر ضمیمه پست" />
      )}

      <div className="post-card__meta">
        <span>{number.format(likeCount)} پسند</span>
        <span>{number.format(commentCount)} دیدگاه</span>
      </div>
      <footer className="post-card__actions">
        <button
          type="button"
          className={liked ? "post-action post-action--liked" : "post-action"}
          onClick={toggleLike}
        >
          <Heart size={19} fill={liked ? "currentColor" : "none"} />
          {liked ? "پسندیدم" : "پسندیدن"}
        </button>
        <button
          type="button"
          className="post-action"
          onClick={() => setShowComments((value) => !value)}
        >
          <MessageCircle size={19} />
          گفتگو
        </button>
        <button type="button" className="post-action" onClick={share}>
          <Send size={18} />
          اشتراک
        </button>
      </footer>
      {showComments && (
        <CommentBox
          postId={post.id}
          onCountChange={(amount) => setCommentCount((count) => count + amount)}
        />
      )}
    </article>
  );
}

function Composer({ profile, onCreated, onError }) {
  const [expanded, setExpanded] = useState(false);
  const [postType, setPostType] = useState("general");
  const [submitting, setSubmitting] = useState(false);
  const formRef = useRef(null);

  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    form.set("post_type", postType);
    form.set("status", "published");
    if (postType === "workout") {
      form.set(
        "workout",
        JSON.stringify({
          exercise_type: form.get("exercise_type"),
          weight_kg: form.get("weight_kg") || null,
          repetitions: form.get("repetitions") || null,
          duration_seconds: form.get("duration_seconds") || null,
        }),
      );
    }
    ["exercise_type", "weight_kg", "repetitions", "duration_seconds"].forEach((key) =>
      form.delete(key),
    );
    if (!form.get("media")?.size) form.delete("media");

    setSubmitting(true);
    try {
      const post = await api.createPost(form);
      onCreated(post);
      formRef.current?.reset();
      setExpanded(false);
      setPostType("general");
    } catch (error) {
      onError(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="card composer" onSubmit={submit} ref={formRef}>
      <div className="composer__top">
        <Avatar profile={profile} />
        <label className="sr-only" htmlFor="post-body">
          متن پست
        </label>
        <textarea
          id="post-body"
          name="body"
          required
          maxLength={5000}
          rows={expanded ? 3 : 1}
          placeholder="امروز چه قدمی برای سلامتی‌ات برداشتی؟"
          onFocus={() => setExpanded(true)}
        />
      </div>
      {expanded && (
        <>
          {postType === "workout" && (
            <div className="composer__workout">
              <label>
                نوع تمرین
                <input name="exercise_type" required placeholder="مثلاً اسکوات" />
              </label>
              <label>
                وزن (کیلو)
                <input name="weight_kg" type="number" min="0" step="0.25" />
              </label>
              <label>
                تکرار
                <input name="repetitions" type="number" min="0" />
              </label>
              <label>
                مدت (ثانیه)
                <input name="duration_seconds" type="number" min="0" />
              </label>
            </div>
          )}
          <div className="composer__actions">
            <label className="attachment">
              <ImagePlus size={18} />
              تصویر
              <input name="media" type="file" accept="image/jpeg,image/png,image/webp" />
            </label>
            <button
              type="button"
              className={postType === "workout" ? "attachment attachment--active" : "attachment"}
              onClick={() => setPostType((value) => (value === "workout" ? "general" : "workout"))}
            >
              <Dumbbell size={18} />
              رکورد ورزشی
            </button>
            <button
              type="button"
              className={postType === "progress" ? "attachment attachment--active" : "attachment"}
              onClick={() => setPostType((value) => (value === "progress" ? "general" : "progress"))}
            >
              <BarChart3 size={18} />
              نمودار پیشرفت
            </button>
            <button className="button button--primary composer__submit" disabled={submitting}>
              {submitting ? "در حال انتشار…" : "انتشار"}
            </button>
          </div>
        </>
      )}
    </form>
  );
}

export default function Feed({
  profile,
  notify,
  focusPostId,
  onOpenProfile,
  onNavigate,
}) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await api.feed();
      const feedItems = results(payload);
      if (focusPostId && !feedItems.some((item) => item.id === focusPostId)) {
        const focusedPost = await api.post(focusPostId);
        feedItems.unshift(focusedPost);
      }
      setPosts(feedItems);
      if (focusPostId) {
        window.setTimeout(() => {
          document
            .getElementById(`post-${focusPostId}`)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 120);
      }
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusPostId]);

  return (
    <div className="page-grid page-grid--feed">
      <section className="feed-column">
        <div className="page-heading page-heading--compact">
          <div>
            <span className="eyebrow">جامعه PolyLife</span>
            <h1>فید شخصی تو</h1>
          </div>
          <span className="live-pill">
            <span />
            تازه‌ها
          </span>
        </div>
        <Composer
          profile={profile}
          onCreated={(post) => {
            setPosts((items) => [post, ...items]);
            notify("رکوردت منتشر شد و به فید دنبال‌کننده‌ها رسید.");
          }}
          onError={(message) => notify(message, "error")}
        />
        {error && <ErrorNotice message={error} retry={load} />}
        {loading ? (
          <Loading label="فیدت را آماده می‌کنیم…" />
        ) : posts.length ? (
          posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onChanged={notify}
              onError={(message) => notify(message, "error")}
              onOpenProfile={onOpenProfile}
              focused={post.id === focusPostId}
            />
          ))
        ) : (
          <EmptyState
            icon={Sparkles}
            title="فیدت آماده‌ی شروع است"
            description="چند ورزشکار یا مربی را دنبال کن، یا اولین رکوردت را همین‌جا منتشر کن."
          />
        )}
      </section>

      <aside className="rail">
        <button
          type="button"
          className="card insight-card insight-card--button"
          onClick={() => onNavigate?.("activity")}
        >
          <span className="eyebrow">این هفته</span>
          <div className="insight-card__icon">
            <BarChart3 />
          </div>
          <strong>۳ فعالیت ثبت‌شده</strong>
          <p>یک قدم کوچک دیگر تا ساختن زنجیره‌ی هفتگی.</p>
          <div className="week-dots" aria-label="فعالیت هفتگی">
            {["ش", "ی", "د", "س", "چ", "پ", "ج"].map((day, index) => (
              <span key={day} className={index < 3 ? "done" : ""}>
                {day}
              </span>
            ))}
          </div>
          <span className="text-button">دیدن جزئیات فعالیت‌ها</span>
        </button>
        <section className="card tips-card">
          <span className="eyebrow">پیشنهاد امروز</span>
          <h2>گرم‌کردن را رد نکن</h2>
          <p>۵ تا ۱۰ دقیقه گرم‌کردن پویا، کیفیت ست‌های اصلی را بهتر می‌کند.</p>
          <span className="tips-card__by">از تیم مربیان PolyLife</span>
        </section>
      </aside>
    </div>
  );
}
