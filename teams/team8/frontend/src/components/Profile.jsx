import {
  Award,
  CalendarDays,
  Edit3,
  FileText,
  MapPin,
  ReceiptText,
  Save,
  UserRoundCheck,
  UsersRound,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { Avatar, ErrorNotice, Loading } from "./UI";

const roleNames = {
  athlete: "ورزشکار",
  coach: "مربی",
  sports_doctor: "پزشک ورزشی",
  nutrition_specialist: "متخصص تغذیه",
  admin: "مدیر محتوا",
};

export default function Profile({
  profile: initialProfile,
  onUpdated,
  notify,
  onNavigate,
}) {
  const [profile, setProfile] = useState(initialProfile);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [activities, setActivities] = useState([]);
  const [purchases, setPurchases] = useState([]);

  useEffect(() => {
    Promise.all([api.profile(), api.activity("me"), api.purchases()])
      .then(([profilePayload, activityPayload, purchasePayload]) => {
        setProfile(profilePayload);
        setActivities(activityPayload);
        setPurchases(purchasePayload.results || purchasePayload);
      })
      .catch((reason) => setError(reason.message));
  }, []);

  const openActivity = (item) => {
    const contexts = {
      feed: { postId: item.target_id },
      member: { profileId: Number(item.target_id) },
      messages: { userId: Number(item.target_id) },
      courses: { courseId: item.target_id },
    };
    onNavigate(item.target_page, contexts[item.target_page] || null);
  };

  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const avatar = form.get("avatar");
    if (avatar instanceof File && avatar.size === 0) form.delete("avatar");
    setSaving(true);
    try {
      const updated = await api.updateProfile(form);
      setProfile(updated);
      onUpdated(updated);
      setEditing(false);
      notify("پروفایلت با موفقیت به‌روز شد.");
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setSaving(false);
    }
  };

  if (error) return <ErrorNotice message={error} />;
  if (!profile) return <Loading label="پروفایلت را آماده می‌کنیم…" />;

  return (
    <section className="profile-page">
      <div className="profile-hero">
        <div className="profile-hero__pattern" />
        <div className="profile-hero__content">
          <Avatar profile={profile} size="xlarge" />
          <div>
            <span className="eyebrow">{roleNames[profile.role]}</span>
            <h1>{profile.display_name || profile.username}</h1>
            <p>@{profile.username}</p>
          </div>
          <button type="button" className="button button--cream" onClick={() => setEditing((value) => !value)}>
            <Edit3 size={17} />
            {editing ? "انصراف" : "ویرایش پروفایل"}
          </button>
        </div>
      </div>

      <div className="profile-layout">
        <div>
          {editing ? (
            <form className="card profile-form" onSubmit={submit}>
              <div className="section-heading">
                <div>
                  <span className="eyebrow">تنظیمات عمومی</span>
                  <h2>ویرایش معرفی حرفه‌ای</h2>
                </div>
              </div>
              <div className="form-grid">
                <label>
                  نام نمایشی
                  <input name="display_name" defaultValue={profile.display_name} maxLength={150} />
                </label>
                <label>
                  تصویر پروفایل
                  <input name="avatar" type="file" accept="image/jpeg,image/png,image/webp" />
                  <small>JPG، PNG یا WebP؛ حداکثر ۵ مگابایت</small>
                </label>
                <label>
                  نقش
                  <select name="role" defaultValue={profile.role} disabled={profile.is_verified}>
                    <option value="athlete">ورزشکار</option>
                    <option value="coach">مربی</option>
                    <option value="sports_doctor">پزشک ورزشی</option>
                    <option value="nutrition_specialist">متخصص تغذیه</option>
                  </select>
                  <small>
                    {profile.is_verified
                      ? "نقش پروفایل تأییدشده فقط توسط مدیر سامانه تغییر می‌کند."
                      : "نقش حرفه‌ای خود را انتخاب کنید؛ دسترسی تخصصی پس از تأیید مدیر فعال می‌شود."}
                  </small>
                </label>
                <label>
                  تخصص
                  <input name="specialization" defaultValue={profile.specialization} />
                </label>
                <label>
                  شهر
                  <input name="location" defaultValue={profile.location} />
                </label>
                <label>
                  سال تجربه
                  <input name="experience_years" type="number" min="0" max="80" defaultValue={profile.experience_years} />
                </label>
                <label className="form-field--full">
                  درباره من
                  <textarea name="bio" rows="5" maxLength={1000} defaultValue={profile.bio} />
                </label>
              </div>
              <button className="button button--primary" disabled={saving}>
                <Save size={18} />
                {saving ? "در حال ذخیره…" : "ذخیره تغییرات"}
              </button>
            </form>
          ) : (
            <>
              <article className="card profile-about">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">درباره من</span>
                    <h2>داستان مسیر سلامتی</h2>
                  </div>
                </div>
                <p>{profile.bio || "هنوز توضیحی برای پروفایل نوشته نشده است."}</p>
                <div className="profile-facts">
                  {profile.specialization && (
                    <span>
                      <Award size={18} />
                      {profile.specialization}
                    </span>
                  )}
                  {profile.location && (
                    <span>
                      <MapPin size={18} />
                      {profile.location}
                    </span>
                  )}
                  <span>
                    <CalendarDays size={18} />
                    {profile.experience_years.toLocaleString("fa-IR")} سال تجربه
                  </span>
                </div>
              </article>
              <article className="card profile-activity">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">فعالیت</span>
                    <h2>ردپای من در جامعه</h2>
                  </div>
                </div>
                <div className="profile-activity-list">
                  {activities.slice(0, 5).map((item) => (
                    <button
                      type="button"
                      key={item.id}
                      onClick={() => openActivity(item)}
                    >
                      <FileText size={19} />
                      <span>
                        <strong>{item.title}</strong>
                        <small>{item.description}</small>
                      </span>
                      <b>باز کردن</b>
                    </button>
                  ))}
                  {!activities.length && (
                    <div className="activity-placeholder">
                      <FileText size={26} />
                      <span>هنوز فعالیتی برای نمایش ثبت نشده است.</span>
                    </div>
                  )}
                </div>
                {activities.length > 5 && (
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => onNavigate("activity")}
                  >
                    مشاهده همه فعالیت‌ها
                  </button>
                )}
              </article>
              <article className="card profile-purchases">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">سابقه خرید</span>
                    <h2>دوره‌های خریداری‌شده</h2>
                  </div>
                  <ReceiptText size={23} />
                </div>
                {purchases.length ? (
                  <div className="profile-purchase-list">
                    {purchases.slice(0, 3).map((purchase) => (
                      <button
                        type="button"
                        key={purchase.id}
                        onClick={() =>
                          onNavigate("courses", { courseId: purchase.course.id })
                        }
                      >
                        <span>
                          <strong>{purchase.course.title}</strong>
                          <small dir="ltr">{purchase.reference}</small>
                        </span>
                        <b>{purchase.amount.toLocaleString("fa-IR")} تومان</b>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="muted">هنوز خرید دوره‌ای برای این حساب ثبت نشده است.</p>
                )}
                <button
                  type="button"
                  className="text-button"
                  onClick={() => onNavigate("transactions")}
                >
                  مشاهده همه تراکنش‌ها
                </button>
              </article>
            </>
          )}
        </div>

        <aside className="profile-rail">
          <div className="card profile-numbers">
            <span>
              <UsersRound size={20} />
              <strong>{profile.followers_count.toLocaleString("fa-IR")}</strong>
              دنبال‌کننده
            </span>
            <span>
              <UserRoundCheck size={20} />
              <strong>{profile.following_count.toLocaleString("fa-IR")}</strong>
              دنبال‌شده
            </span>
            <span>
              <FileText size={20} />
              <strong>{profile.posts_count.toLocaleString("fa-IR")}</strong>
              پست
            </span>
          </div>
          {profile.badge && (
            <div className="card badge-card">
              <Award size={29} />
              <span className="eyebrow">نشان تخصصی</span>
              <strong>{profile.badge}</strong>
              <p>این نشان بر اساس نقش حرفه‌ای شما نمایش داده می‌شود.</p>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}
