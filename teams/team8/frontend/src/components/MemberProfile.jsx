import {
  ArrowRight,
  Award,
  BadgeCheck,
  MapPin,
  MessageCircle,
  UserMinus,
  UserPlus,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, results } from "../api";
import { Avatar, EmptyState, ErrorNotice, Loading } from "./UI";
import { PostCard } from "./Feed";

const roleNames = {
  athlete: "ورزشکار",
  coach: "مربی",
  sports_doctor: "پزشک ورزشی",
  nutrition_specialist: "متخصص تغذیه",
  admin: "مدیر محتوا",
};

export default function MemberProfile({
  userId,
  currentUserId,
  notify,
  onBack,
  onMessage,
  onOpenProfile,
}) {
  const [profile, setProfile] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [profilePayload, postPayload] = await Promise.all([
        api.profileById(userId),
        api.postsByAuthor(userId),
      ]);
      setProfile(profilePayload);
      setPosts(results(postPayload));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const toggleFollow = async () => {
    try {
      const response = await api.follow(profile.user_id, !profile.is_following);
      setProfile((value) => ({
        ...value,
        is_following: response.following,
        followers_count: value.followers_count + (response.following ? 1 : -1),
      }));
      notify(response.following ? "این کاربر را دنبال می‌کنی." : "دنبال‌کردن متوقف شد.");
    } catch (reason) {
      notify(reason.message, "error");
    }
  };

  if (loading) return <Loading label="پروفایل و فعالیت‌های کاربر را باز می‌کنیم…" />;
  if (error) return <ErrorNotice message={error} retry={load} />;
  if (!profile) return null;

  return (
    <section className="member-page">
      <button type="button" className="back-button" onClick={onBack}>
        <ArrowRight size={18} />
        بازگشت به کشف کاربران
      </button>

      <div className="member-hero">
        <div className="member-hero__identity">
          <Avatar profile={profile} size="xlarge" />
          <div>
            <span className="eyebrow">{roleNames[profile.role]}</span>
            <h1>
              {profile.display_name || profile.username}
              {profile.is_verified && <BadgeCheck size={22} />}
            </h1>
            <p>@{profile.username}</p>
          </div>
        </div>
        <p className="member-hero__bio">
          {profile.bio || "این کاربر هنوز معرفی کوتاهی ننوشته است."}
        </p>
        <div className="member-hero__facts">
          {profile.specialization && (
            <span>
              <Award size={17} />
              {profile.specialization}
            </span>
          )}
          {profile.location && (
            <span>
              <MapPin size={17} />
              {profile.location}
            </span>
          )}
          <span>{profile.followers_count.toLocaleString("fa-IR")} دنبال‌کننده</span>
          <span>{profile.posts_count.toLocaleString("fa-IR")} پست</span>
        </div>
        {profile.user_id !== currentUserId && (
          <div className="member-hero__actions">
            <button
              type="button"
              className={profile.is_following ? "button button--secondary" : "button button--primary"}
              onClick={toggleFollow}
            >
              {profile.is_following ? <UserMinus size={18} /> : <UserPlus size={18} />}
              {profile.is_following ? "دنبال می‌کنم" : "دنبال کردن"}
            </button>
            <button
              type="button"
              className="button button--cream"
              onClick={() => onMessage(profile.user_id)}
            >
              <MessageCircle size={18} />
              ارسال پیام مستقیم
            </button>
          </div>
        )}
      </div>

      <div className="section-heading member-posts-heading">
        <div>
          <span className="eyebrow">فعالیت عمومی</span>
          <h2>پست‌ها و تجربه‌های {profile.display_name || profile.username}</h2>
        </div>
      </div>
      <div className="member-posts">
        {posts.length ? (
          posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onChanged={notify}
              onError={(message) => notify(message, "error")}
              onOpenProfile={onOpenProfile}
            />
          ))
        ) : (
          <EmptyState
            title="هنوز پستی منتشر نشده"
            description="وقتی این کاربر تجربه‌ای منتشر کند، اینجا نمایش داده می‌شود."
          />
        )}
      </div>
    </section>
  );
}
