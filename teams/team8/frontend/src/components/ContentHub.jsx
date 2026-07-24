import {
  ArrowLeft,
  BookOpenText,
  Clock3,
  Filter,
  Play,
  SearchX,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, results } from "../api";
import { EmptyState, ErrorNotice, Loading, SearchField, Stars } from "./UI";

const number = new Intl.NumberFormat("fa-IR");
const typeNames = {
  article: "مقاله",
  video: "ویدیو",
  training_plan: "برنامه تمرینی",
  diet_plan: "برنامه رژیمی",
};
const difficultyNames = {
  beginner: "مبتدی",
  intermediate: "متوسط",
  advanced: "پیشرفته",
};

function ContentCard({ item, onOpen }) {
  return (
    <article className="content-card">
      <button type="button" className="content-card__cover" onClick={() => onOpen(item)}>
        {item.thumbnail_url ? (
          <img src={item.thumbnail_url} alt="" />
        ) : (
          <span className="cover-pattern">
            {item.content_type === "video" ? <Play size={28} /> : <BookOpenText size={28} />}
          </span>
        )}
        <span className="content-card__type">{typeNames[item.content_type]}</span>
      </button>
      <div className="content-card__body">
        <div className="content-card__author">
          <span>{item.author_username}</span>
          <span>•</span>
          <span>{item.category.name}</span>
        </div>
        <h2>{item.title}</h2>
        <p>{item.body.slice(0, 105)}{item.body.length > 105 ? "…" : ""}</p>
        <div className="content-card__footer">
          <span>
            <Clock3 size={16} />
            {number.format(item.duration_minutes)} دقیقه
          </span>
          <span>{difficultyNames[item.difficulty]}</span>
          <Stars value={Math.round(item.average_rating || 0)} />
        </div>
      </div>
    </article>
  );
}

function ContentDetail({ item, onClose, notify, onRated }) {
  if (!item) return null;
  const rate = async (score) => {
    try {
      await api.rateContent(item.id, score);
      onRated(item.id, score);
      notify("امتیازت ثبت شد؛ ممنون که به جامعه کمک می‌کنی.");
    } catch (error) {
      notify(error.message, "error");
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <article
        className="modal content-detail"
        role="dialog"
        aria-modal="true"
        aria-labelledby="content-detail-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal__close" onClick={onClose}>
          بستن
        </button>
        <span className="eyebrow">
          {typeNames[item.content_type]} · {item.category.full_path}
        </span>
        <h2 id="content-detail-title">{item.title}</h2>
        <div className="content-detail__meta">
          <span>نویسنده: {item.author_username}</span>
          <span>{difficultyNames[item.difficulty]}</span>
          <span>{number.format(item.duration_minutes)} دقیقه</span>
        </div>
        {item.media_url && item.content_type === "video" && (
          <video className="content-detail__video" controls preload="metadata">
            <source src={item.media_url} />
          </video>
        )}
        <p className="content-detail__body">{item.body}</p>
        <div className="tag-list">
          {item.tags.map((tag) => (
            <span key={tag}>#{tag}</span>
          ))}
        </div>
        <div className="content-detail__rating">
          <div>
            <strong>این محتوا چقدر مفید بود؟</strong>
            <small>{number.format(item.rating_count)} نفر امتیاز داده‌اند</small>
          </div>
          <Stars value={item.my_rating || 0} onChange={rate} />
        </div>
      </article>
    </div>
  );
}

export default function ContentHub({ notify }) {
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [category, setCategory] = useState("");
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (type) params.set("type", type);
    if (difficulty) params.set("difficulty", difficulty);
    if (category) params.set("category", category);
    api
      .contents(params.toString())
      .then((payload) => setItems(results(payload)))
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    api.categories().then((payload) => setCategories(results(payload))).catch(() => {});
    load();
    // Initial load intentionally runs once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">یادگیری از متخصصان</span>
          <h1>هاب محتوای آموزشی</h1>
          <p>محتوای معتبر و دسته‌بندی‌شده برای بهتر تمرین‌کردن و سالم‌تر زندگی‌کردن.</p>
        </div>
        <div className="heading-stat">
          <Sparkles size={21} />
          <span>
            <strong>دانش کاربردی</strong>
            <small>منتخب مربیان و متخصصان</small>
          </span>
        </div>
      </div>

      <div className="card filter-panel">
        <SearchField
          value={query}
          onChange={setQuery}
          placeholder="عنوان، موضوع یا برچسب…"
          onSubmit={(event) => {
            event.preventDefault();
            load();
          }}
        />
        <div className="filters">
          <SlidersHorizontal size={18} />
          <select value={type} onChange={(event) => setType(event.target.value)}>
            <option value="">همه قالب‌ها</option>
            <option value="article">مقاله</option>
            <option value="video">ویدیو</option>
            <option value="training_plan">برنامه تمرینی</option>
            <option value="diet_plan">برنامه رژیمی</option>
          </select>
          <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
            <option value="">همه سطح‌ها</option>
            <option value="beginner">مبتدی</option>
            <option value="intermediate">متوسط</option>
            <option value="advanced">پیشرفته</option>
          </select>
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">همه دسته‌ها</option>
            {categories.map((item) => (
              <option value={item.id} key={item.id}>
                {item.full_path}
              </option>
            ))}
          </select>
          <button type="button" className="button button--secondary" onClick={load}>
            <Filter size={17} />
            اعمال فیلتر
          </button>
        </div>
      </div>

      {error && <ErrorNotice message={error} retry={load} />}
      {loading ? (
        <Loading label="کتابخانه را مرور می‌کنیم…" />
      ) : items.length ? (
        <>
          <div className="section-heading">
            <div>
              <h2>تازه‌ترین آموزش‌ها</h2>
              <span>{number.format(items.length)} نتیجه</span>
            </div>
            <button type="button" className="text-button" onClick={load}>
              تازه‌سازی
              <ArrowLeft size={17} />
            </button>
          </div>
          <div className="content-grid">
            {items.map((item) => (
              <ContentCard key={item.id} item={item} onOpen={setSelected} />
            ))}
          </div>
        </>
      ) : (
        <EmptyState
          icon={SearchX}
          title="محتوایی با این فیلتر پیدا نشد"
          description="عبارت جستجو یا یکی از فیلترها را تغییر بده."
        />
      )}

      <ContentDetail
        item={selected}
        onClose={() => setSelected(null)}
        notify={notify}
        onRated={(id, score) => {
          setItems((values) =>
            values.map((item) => (item.id === id ? { ...item, my_rating: score } : item)),
          );
          setSelected((item) => ({ ...item, my_rating: score }));
        }}
      />
    </section>
  );
}

