import { FileVideo2, Save, Send, Tags } from "lucide-react";
import { useEffect, useState } from "react";
import { api, results } from "../api";
import { ErrorNotice, Loading } from "./UI";

export default function Studio({ notify, onNavigate }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .categories()
      .then((payload) => setCategories(results(payload)))
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    const status = event.nativeEvent.submitter?.value || "published";
    const form = new FormData(event.currentTarget);
    form.set("status", status);
    form.set(
      "tag_names",
      JSON.stringify(
        String(form.get("tags") || "")
          .split(/[,،]/)
          .map((tag) => tag.trim())
          .filter(Boolean),
      ),
    );
    form.delete("tags");
    if (!form.get("media")?.size) form.delete("media");
    if (!form.get("thumbnail")?.size) form.delete("thumbnail");

    setSaving(true);
    try {
      await api.createContent(form);
      notify(status === "published" ? "محتوا منتشر و در هاب قابل جستجو شد." : "پیش‌نویس ذخیره شد.");
      event.currentTarget.reset();
      if (status === "published") onNavigate("hub");
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Loading label="استودیوی محتوا را آماده می‌کنیم…" />;
  if (error) return <ErrorNotice message={error} />;

  return (
    <section className="studio-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">پنل مربی و متخصص</span>
          <h1>استودیوی محتوای آموزشی</h1>
          <p>دانش کاربردی خود را ساختاریافته، قابل جستجو و در دسترس جامعه منتشر کن.</p>
        </div>
      </div>
      <form className="card studio-form" onSubmit={submit}>
        <div className="studio-form__main">
          <label>
            عنوان محتوا
            <input name="title" required maxLength={240} placeholder="یک عنوان روشن و کاربردی" />
          </label>
          <label>
            توضیحات آموزشی
            <textarea name="body" required rows="12" placeholder="مطلب را مرحله‌به‌مرحله و دقیق توضیح دهید…" />
          </label>
          <div className="upload-grid">
            <label className="upload-box">
              <FileVideo2 size={25} />
              <strong>فایل ویدیو</strong>
              <small>MP4 یا WebM، حداکثر ۲۰۰ مگابایت</small>
              <input name="media" type="file" accept="video/mp4,video/webm" />
            </label>
            <label className="upload-box">
              <FileVideo2 size={25} />
              <strong>تصویر کاور</strong>
              <small>JPG، PNG یا WebP، حداکثر ۵ مگابایت</small>
              <input name="thumbnail" type="file" accept="image/jpeg,image/png,image/webp" />
            </label>
          </div>
        </div>
        <aside className="studio-form__settings">
          <h2>تنظیمات انتشار</h2>
          <label>
            قالب محتوا
            <select name="content_type" defaultValue="article">
              <option value="article">مقاله</option>
              <option value="video">ویدیو</option>
              <option value="training_plan">برنامه تمرینی</option>
              <option value="diet_plan">برنامه رژیمی</option>
            </select>
          </label>
          <label>
            دسته‌بندی
            <select name="category" required defaultValue="">
              <option value="" disabled>انتخاب دسته</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>{category.full_path}</option>
              ))}
            </select>
          </label>
          <label>
            سطح
            <select name="difficulty" defaultValue="beginner">
              <option value="beginner">مبتدی</option>
              <option value="intermediate">متوسط</option>
              <option value="advanced">پیشرفته</option>
            </select>
          </label>
          <label>
            مدت مطالعه/تماشا (دقیقه)
            <input name="duration_minutes" type="number" min="0" defaultValue="5" />
          </label>
          <label>
            <span className="label-with-icon"><Tags size={16} /> برچسب‌ها</span>
            <input name="tags" placeholder="گرم‌کردن، مبتدی، بدنسازی" />
          </label>
          <div className="studio-form__actions">
            <button
              type="submit"
              name="intent"
              value="draft"
              className="button button--secondary"
              disabled={saving}
            >
              <Save size={17} />
              ذخیره پیش‌نویس
            </button>
            <button
              type="submit"
              name="intent"
              value="published"
              className="button button--primary"
              disabled={saving}
            >
              <Send size={17} />
              {saving ? "در حال ذخیره…" : "انتشار محتوا"}
            </button>
          </div>
        </aside>
      </form>
    </section>
  );
}
