import {
  ArrowLeft,
  BookMarked,
  CheckCircle2,
  Clock3,
  FileText,
  GraduationCap,
  LockKeyhole,
  PlayCircle,
  ShoppingCart,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, results } from "../api";
import { EmptyState, ErrorNotice, Loading } from "./UI";

const number = new Intl.NumberFormat("fa-IR");

function ProgressBar({ value }) {
  return (
    <div className="progress" aria-label={`${value} درصد پیشرفت`}>
      <span style={{ width: `${value}%` }} />
    </div>
  );
}

function LessonViewer({ lesson, course, progress, busy, onClose, onComplete }) {
  if (!lesson) return null;
  const content = lesson.content_detail;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <article
        className="modal lesson-viewer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lesson-viewer-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal__close" onClick={onClose}>
          بستن
        </button>
        <span className="eyebrow">
          درس {number.format(lesson.order)} از {number.format(course.lessons.length)}
        </span>
        <h2 id="lesson-viewer-title">{lesson.title}</h2>
        <div className="lesson-viewer__meta">
          <span>
            <Clock3 size={17} />
            {number.format(lesson.duration_minutes)} دقیقه
          </span>
          <span>
            {lesson.is_preview ? <PlayCircle size={17} /> : <BookMarked size={17} />}
            {lesson.is_preview ? "پیش‌نمایش عمومی" : course.title}
          </span>
        </div>

        {content?.media_url && content.content_type === "video" && (
          <video className="lesson-viewer__video" controls src={content.media_url}>
            مرورگر شما پخش ویدیو را پشتیبانی نمی‌کند.
          </video>
        )}
        {content?.thumbnail_url && !content.media_url && (
          <img
            className="lesson-viewer__image"
            src={content.thumbnail_url}
            alt={content.title}
          />
        )}
        {content && (
          <section className="lesson-content-block">
            <span className="eyebrow">محتوای مرتبط</span>
            <h3>{content.title}</h3>
            <p>{content.body}</p>
          </section>
        )}
        <section className="lesson-content-block lesson-content-block--primary">
          <span className="eyebrow">متن درس</span>
          <p>{lesson.body || "محتوای این درس به‌زودی تکمیل می‌شود."}</p>
        </section>

        {progress && (
          <button
            type="button"
            className="button button--primary button--wide"
            disabled={progress.is_completed || busy}
            onClick={() => onComplete(lesson.id)}
          >
            <CheckCircle2 size={18} />
            {progress.is_completed ? "این درس تکمیل شده" : "مطالعه کردم؛ ثبت تکمیل درس"}
          </button>
        )}
      </article>
    </div>
  );
}

function CourseDetail({
  course,
  enrollment,
  onClose,
  onEnroll,
  onAddCart,
  onOpenLesson,
  busy,
}) {
  if (!course) return null;
  const progressByLesson = new Map(
    enrollment?.lesson_progress?.map((item) => [item.lesson.id, item]) || [],
  );
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <article
        className="modal course-detail"
        role="dialog"
        aria-modal="true"
        aria-labelledby="course-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal__close" onClick={onClose}>
          بستن
        </button>
        <span className="eyebrow">
          {course.is_free ? "دوره رایگان" : `${number.format(course.price)} تومان`} ·{" "}
          {course.category.name}
        </span>
        <h2 id="course-title">{course.title}</h2>
        <p>{course.description}</p>
        <div className="course-detail__facts">
          <span>
            <GraduationCap size={19} />
            {number.format(course.lessons.length)} درس
          </span>
          <span>
            <Clock3 size={19} />
            {number.format(course.duration_minutes)} دقیقه
          </span>
          <span>
            <BookMarked size={19} />
            {course.author_username}
          </span>
        </div>

        {enrollment && (
          <div className="course-progress-summary">
            <span>
              <strong>پیشرفت تو</strong>
              <small>{number.format(enrollment.progress_percent)}٪</small>
            </span>
            <ProgressBar value={enrollment.progress_percent} />
          </div>
        )}

        <div className="lesson-stack">
          {course.lessons.map((lesson) => {
            const progress = progressByLesson.get(lesson.id);
            const canOpen = Boolean(lesson.accessible);
            return (
              <button
                type="button"
                className={
                  canOpen
                    ? "lesson-row lesson-row--openable"
                    : "lesson-row lesson-row--locked"
                }
                key={lesson.id}
                disabled={!canOpen}
                onClick={() => canOpen && onOpenLesson(lesson, progress)}
              >
                <span className={progress?.is_completed ? "lesson-index done" : "lesson-index"}>
                  {progress?.is_completed ? (
                    <CheckCircle2 size={19} />
                  ) : (
                    number.format(lesson.order)
                  )}
                </span>
                <span>
                  <strong>{lesson.title}</strong>
                  <small>
                    {number.format(lesson.duration_minutes)} دقیقه ·{" "}
                    {canOpen ? "برای مشاهده باز کنید" : "پس از ثبت‌نام در دسترس"}
                  </small>
                </span>
                {canOpen ? (
                  <span className="lesson-preview">
                    {progress?.is_completed ? <CheckCircle2 size={17} /> : <PlayCircle size={17} />}
                    {progress?.is_completed ? "مرور دوباره" : lesson.is_preview ? "پیش‌نمایش" : "باز کردن درس"}
                  </span>
                ) : (
                  <LockKeyhole size={17} className="muted" />
                )}
              </button>
            );
          })}
        </div>

        {!enrollment && course.is_free && (
          <button
            type="button"
            className="button button--primary button--wide"
            onClick={() => onEnroll(course.id)}
            disabled={busy}
          >
            {busy ? "در حال ثبت‌نام…" : "ثبت‌نام رایگان و باز کردن همه درس‌ها"}
          </button>
        )}
        {!enrollment && !course.is_free && !course.purchased && (
          <button
            type="button"
            className="button button--primary button--wide"
            onClick={() => onAddCart(course.id)}
            disabled={busy}
          >
            <ShoppingCart size={19} />
            {busy
              ? "در حال افزودن…"
              : `افزودن به سبد · ${number.format(course.price)} تومان`}
          </button>
        )}
        {!enrollment && !course.is_free && course.purchased && (
          <button
            type="button"
            className="button button--primary button--wide"
            onClick={() => onEnroll(course.id)}
            disabled={busy}
          >
            فعال‌سازی دوره خریداری‌شده
          </button>
        )}
      </article>
    </div>
  );
}

export default function Courses({ notify, onNavigate, initialCourseId }) {
  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [selectedEnrollment, setSelectedEnrollment] = useState(null);
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [selectedProgress, setSelectedProgress] = useState(null);
  const [tab, setTab] = useState("mine");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const openCourse = async (id, currentEnrollments = enrollments) => {
    try {
      const detail = await api.course(id);
      setSelected(detail);
      setSelectedEnrollment(
        currentEnrollments.find((item) => item.course.id === id) || null,
      );
    } catch (reason) {
      notify(reason.message, "error");
    }
  };

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [coursePayload, enrollmentPayload] = await Promise.all([
        api.courses("page_size=50"),
        api.enrollments(),
      ]);
      const courseItems = results(coursePayload);
      const enrollmentItems = results(enrollmentPayload);
      setCourses(courseItems);
      setEnrollments(enrollmentItems);
      if (initialCourseId) await openCourse(initialCourseId, enrollmentItems);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCourseId]);

  const enroll = async (id) => {
    setBusy(true);
    try {
      const enrollment = await api.enroll(id);
      const next = [
        enrollment,
        ...enrollments.filter((item) => item.id !== enrollment.id),
      ];
      setEnrollments(next);
      setSelectedEnrollment(enrollment);
      setSelected(await api.course(id));
      notify("دوره فعال شد؛ همه درس‌ها حالا قابل بازشدن هستند.");
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const addCart = async (id) => {
    setBusy(true);
    try {
      await api.addToCart(id);
      notify("دوره به سبد خرید اضافه شد.");
      setSelected(null);
      onNavigate("cart");
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const complete = async (lessonId) => {
    if (!selectedEnrollment) return;
    setBusy(true);
    try {
      const enrollment = await api.updateLesson(selectedEnrollment.id, lessonId, {
        is_completed: true,
        watched_seconds: (selectedLesson?.duration_minutes || 0) * 60,
      });
      setSelectedEnrollment(enrollment);
      setSelectedProgress(
        enrollment.lesson_progress.find((item) => item.lesson.id === lessonId),
      );
      setEnrollments((items) =>
        items.map((item) => (item.id === enrollment.id ? enrollment : item)),
      );
      notify(
        enrollment.progress_percent === 100
          ? "تبریک! دوره را با موفقیت به پایان رساندی."
          : "پیشرفت این درس با جزئیات ذخیره شد.",
      );
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const catalog = courses.filter((course) => course.status === "published");

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">مسیر یادگیری</span>
          <h1>دوره‌های آموزشی</h1>
          <p>درس‌ها را واقعاً باز کن، بخوان و پیشرفت هر درس را ثبت کن.</p>
        </div>
        <button
          type="button"
          className="button button--secondary"
          onClick={() => onNavigate("cart")}
        >
          <ShoppingCart size={18} />
          سبد خرید
        </button>
      </div>
      <div className="segmented" role="tablist">
        <button
          type="button"
          className={tab === "mine" ? "active" : ""}
          onClick={() => setTab("mine")}
        >
          دوره‌های من
          <span>{number.format(enrollments.length)}</span>
        </button>
        <button
          type="button"
          className={tab === "catalog" ? "active" : ""}
          onClick={() => setTab("catalog")}
        >
          کشف دوره‌ها
          <span>{number.format(catalog.length)}</span>
        </button>
      </div>

      {error && <ErrorNotice message={error} retry={load} />}
      {loading ? (
        <Loading label="مسیرهای یادگیری را آماده می‌کنیم…" />
      ) : tab === "mine" ? (
        enrollments.length ? (
          <div className="course-grid">
            {enrollments.map((enrollment) => (
              <article className="card enrolled-card" key={enrollment.id}>
                <div className="enrolled-card__cover">
                  <GraduationCap size={31} />
                  <span>{enrollment.course.category_name}</span>
                </div>
                <div>
                  <span className="eyebrow">
                    {enrollment.status === "completed" ? "تکمیل‌شده" : "در حال یادگیری"}
                  </span>
                  <h2>{enrollment.course.title}</h2>
                  <ProgressBar value={enrollment.progress_percent} />
                  <div className="enrolled-card__progress">
                    <span>{number.format(enrollment.progress_percent)}٪ پیشرفت</span>
                    <span>{number.format(enrollment.course.lesson_count)} درس</span>
                  </div>
                  <button
                    type="button"
                    className="button button--primary button--wide"
                    onClick={() => openCourse(enrollment.course.id)}
                  >
                    باز کردن درس‌ها
                    <ArrowLeft size={18} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={GraduationCap}
            title="هنوز دوره‌ای شروع نکرده‌ای"
            description="از کاتالوگ، یک دوره رایگان یا پولی متناسب با هدفت انتخاب کن."
            action={
              <button type="button" className="button button--primary" onClick={() => setTab("catalog")}>
                دیدن دوره‌ها
              </button>
            }
          />
        )
      ) : (
        <div className="course-grid">
          {catalog.map((course) => (
            <article className="card catalog-card" key={course.id}>
              <div className="catalog-card__cover">
                {course.cover_url ? (
                  <img src={course.cover_url} alt="" />
                ) : (
                  <GraduationCap size={34} />
                )}
                <span>
                  {course.is_free ? "رایگان" : `${number.format(course.price)} تومان`}
                </span>
              </div>
              <div className="catalog-card__body">
                <span className="eyebrow">{course.category_name}</span>
                <h2>{course.title}</h2>
                <div className="catalog-card__meta">
                  <span>{number.format(course.lesson_count)} درس</span>
                  <span>{number.format(course.duration_minutes)} دقیقه</span>
                </div>
                <button
                  type="button"
                  className="button button--secondary button--wide"
                  onClick={() => openCourse(course.id)}
                >
                  <FileText size={17} />
                  مشاهده دوره و درس‌ها
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <CourseDetail
        course={selected}
        enrollment={selectedEnrollment}
        onClose={() => setSelected(null)}
        onEnroll={enroll}
        onAddCart={addCart}
        onOpenLesson={(lesson, progress) => {
          setSelectedLesson(lesson);
          setSelectedProgress(progress);
        }}
        busy={busy}
      />
      <LessonViewer
        lesson={selectedLesson}
        course={selected}
        progress={selectedProgress}
        busy={busy}
        onClose={() => setSelectedLesson(null)}
        onComplete={complete}
      />
    </section>
  );
}
