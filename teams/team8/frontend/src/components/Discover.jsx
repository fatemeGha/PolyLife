import {
  BadgeCheck,
  Eye,
  MapPin,
  MessageCircle,
  SearchX,
  UserMinus,
  UserPlus,
  UsersRound,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, results } from "../api";
import { Avatar, EmptyState, ErrorNotice, Loading, SearchField } from "./UI";

const roleNames = {
  athlete: "ورزشکار",
  coach: "مربی",
  sports_doctor: "پزشک ورزشی",
  nutrition_specialist: "متخصص تغذیه",
  admin: "مدیر محتوا",
};

export default function Discover({
  currentUserId,
  notify,
  onOpenProfile,
  onMessage,
}) {
  const [profiles, setProfiles] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    api
      .profiles(query)
      .then((payload) => setProfiles(results(payload)))
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  };

  // Search runs on submit; this effect only loads the initial discovery list.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  const toggleFollow = async (profile) => {
    try {
      const response = await api.follow(profile.user_id, !profile.is_following);
      setProfiles((items) =>
        items.map((item) =>
          item.user_id === profile.user_id
            ? {
                ...item,
                is_following: response.following,
                followers_count:
                  item.followers_count + (response.following ? 1 : -1),
              }
            : item,
        ),
      );
      notify(response.following ? "به فهرست دنبال‌شده‌ها اضافه شد." : "دنبال‌کردن متوقف شد.");
    } catch (reason) {
      notify(reason.message, "error");
    }
  };

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">شبکه حرفه‌ای ورزش و سلامت</span>
          <h1>آدم‌های الهام‌بخش را پیدا کن</h1>
          <p>ورزشکاران هم‌مسیر، مربیان و متخصصان تأییدشده را دنبال کن.</p>
        </div>
        <span className="heading-icon">
          <UsersRound size={28} />
        </span>
      </div>
      <div className="card discover-search">
        <SearchField
          value={query}
          onChange={setQuery}
          placeholder="نام، نقش یا تخصص…"
          onSubmit={(event) => {
            event.preventDefault();
            load();
          }}
        />
        <button type="button" className="chip" onClick={() => setQuery("مربی")}>
          مربی
        </button>
        <button type="button" className="chip" onClick={() => setQuery("تغذیه")}>
          تغذیه
        </button>
        <button type="button" className="chip" onClick={() => setQuery("بدنسازی")}>
          بدنسازی
        </button>
      </div>

      {error && <ErrorNotice message={error} retry={load} />}
      {loading ? (
        <Loading label="اعضای جامعه را پیدا می‌کنیم…" />
      ) : profiles.length ? (
        <div className="profile-grid">
          {profiles.map((profile) => (
            <article
              className="card person-card person-card--interactive"
              key={profile.user_id}
              role="button"
              tabIndex={0}
              onClick={() => onOpenProfile(profile.user_id)}
              onKeyDown={(event) => {
                if (event.key === "Enter") onOpenProfile(profile.user_id);
              }}
            >
              <div className="person-card__accent" />
              <Avatar profile={profile} size="large" />
              <h2>
                {profile.display_name || profile.username}
                {profile.is_verified && <BadgeCheck size={19} aria-label="تأییدشده" />}
              </h2>
              <span className="person-card__role">{roleNames[profile.role]}</span>
              <p>{profile.bio || "عضو جامعه سلامت PolyLife"}</p>
              <div className="person-card__details">
                <span>{profile.specialization || "سلامت و آمادگی جسمانی"}</span>
                {profile.location && (
                  <span>
                    <MapPin size={15} />
                    {profile.location}
                  </span>
                )}
              </div>
              <div className="person-card__counts">
                <span>
                  <strong>{profile.followers_count.toLocaleString("fa-IR")}</strong>
                  دنبال‌کننده
                </span>
                <span>
                  <strong>{profile.posts_count.toLocaleString("fa-IR")}</strong>
                  پست
                </span>
              </div>
              {profile.user_id !== currentUserId && (
                <div className="person-card__actions">
                  <button
                    type="button"
                    className={profile.is_following ? "button button--secondary" : "button button--primary"}
                    onClick={(event) => {
                      event.stopPropagation();
                      toggleFollow(profile);
                    }}
                  >
                    {profile.is_following ? <UserMinus size={18} /> : <UserPlus size={18} />}
                    {profile.is_following ? "دنبال می‌کنم" : "دنبال کردن"}
                  </button>
                  <button
                    type="button"
                    className="button button--secondary"
                    onClick={(event) => {
                      event.stopPropagation();
                      onMessage(profile.user_id);
                    }}
                  >
                    <MessageCircle size={18} />
                    پیام
                  </button>
                </div>
              )}
              <span className="person-card__open">
                <Eye size={16} />
                مشاهده پروفایل و پست‌ها
              </span>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={SearchX}
          title="کاربری پیدا نشد"
          description="نام یا تخصص را کوتاه‌تر وارد کن."
        />
      )}
    </section>
  );
}
