import {
  Activity,
  Bell,
  BookOpen,
  ChevronDown,
  CircleUserRound,
  GraduationCap,
  Home,
  LogOut,
  Menu,
  MessageCircle,
  PenSquare,
  ReceiptText,
  Search,
  ShoppingBag,
  UsersRound,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Avatar } from "./UI";

const navigation = [
  { id: "feed", label: "فید من", icon: Home },
  { id: "discover", label: "کشف کاربران", icon: UsersRound },
  { id: "messages", label: "پیام‌ها", icon: MessageCircle },
  { id: "hub", label: "هاب محتوا", icon: BookOpen },
  { id: "courses", label: "دوره‌های من", icon: GraduationCap },
  { id: "profile", label: "پروفایل", icon: CircleUserRound },
];

const notificationDate = new Intl.DateTimeFormat("fa-IR", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function targetContext(item) {
  if (item.target_page === "feed") return { postId: item.target_id };
  if (item.target_page === "member") return { profileId: Number(item.target_id) };
  if (item.target_page === "messages") return { userId: Number(item.target_id) };
  if (item.target_page === "courses") return { courseId: item.target_id };
  return null;
}

export default function Shell({ active, onNavigate, profile, children, notify }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const menuRef = useRef(null);
  const canCreate = ["coach", "sports_doctor", "nutrition_specialist", "admin"].includes(
    profile?.role,
  );
  const lastSeen = Number(localStorage.getItem("team8_notification_seen_at") || 0);
  const unreadCount = notifications.filter(
    (item) => item.unread && new Date(item.created_at).getTime() > lastSeen,
  ).length;

  const loadNotifications = async () => {
    setLoadingNotifications(true);
    try {
      setNotifications(await api.activity("notifications"));
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setLoadingNotifications(false);
    }
  };

  useEffect(() => {
    loadNotifications();
    const closeMenus = (event) => {
      if (!menuRef.current?.contains(event.target)) {
        setNotificationOpen(false);
        setAccountOpen(false);
      }
    };
    document.addEventListener("mousedown", closeMenus);
    return () => document.removeEventListener("mousedown", closeMenus);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const navigate = (id, context = null) => {
    onNavigate(id, context);
    setMobileOpen(false);
    setNotificationOpen(false);
    setAccountOpen(false);
  };

  const openNotifications = () => {
    const next = !notificationOpen;
    setNotificationOpen(next);
    setAccountOpen(false);
    if (next) {
      localStorage.setItem("team8_notification_seen_at", String(Date.now()));
      loadNotifications();
    }
  };

  const logout = async () => {
    try {
      await api.logout();
      window.location.assign("http://localhost:8000/login");
    } catch (reason) {
      notify(reason.message, "error");
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <button
          type="button"
          className="icon-button mobile-menu"
          onClick={() => setMobileOpen((value) => !value)}
          aria-label="باز کردن منو"
        >
          {mobileOpen ? <X /> : <Menu />}
        </button>
        <button type="button" className="brand" onClick={() => navigate("feed")}>
          <span className="brand__mark" aria-hidden="true">
            P
          </span>
          <span>
            <strong>PolyLife</strong>
            <small>جامعه‌ی سالم، یادگیری ماندگار</small>
          </span>
        </button>
        <button
          type="button"
          className="topbar__search"
          onClick={() => navigate("discover")}
        >
          <Search size={18} />
          <span>جستجو در جامعه و آموزش</span>
          <kbd>Ctrl K</kbd>
        </button>
        <div className="topbar__actions" ref={menuRef}>
          <div className="topbar-menu-anchor">
            <button
              type="button"
              className="icon-button"
              aria-label="اعلان‌ها"
              onClick={openNotifications}
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="notification-count">
                  {Math.min(unreadCount, 9).toLocaleString("fa-IR")}
                </span>
              )}
            </button>
            {notificationOpen && (
              <div className="topbar-dropdown notification-panel">
                <header>
                  <span>
                    <strong>اعلان‌ها</strong>
                    <small>{notifications.length.toLocaleString("fa-IR")} رویداد اخیر</small>
                  </span>
                  <button type="button" className="text-button" onClick={loadNotifications}>
                    تازه‌سازی
                  </button>
                </header>
                <div className="notification-list">
                  {loadingNotifications ? (
                    <p className="muted">در حال دریافت اعلان‌ها…</p>
                  ) : notifications.length ? (
                    notifications.slice(0, 8).map((item) => (
                      <button
                        type="button"
                        key={item.id}
                        onClick={() => navigate(item.target_page, targetContext(item))}
                      >
                        {item.actor ? (
                          <Avatar profile={item.actor} size="small" />
                        ) : (
                          <span className="notification-icon">
                            <Activity size={17} />
                          </span>
                        )}
                        <span>
                          <strong>{item.title}</strong>
                          <small>{item.description}</small>
                          <time>{notificationDate.format(new Date(item.created_at))}</time>
                        </span>
                      </button>
                    ))
                  ) : (
                    <p className="muted">اعلان تازه‌ای وجود ندارد.</p>
                  )}
                </div>
                <button
                  type="button"
                  className="dropdown-footer"
                  onClick={() => navigate("activity")}
                >
                  مشاهده همه فعالیت‌ها و جزئیات
                </button>
              </div>
            )}
          </div>

          <div className="topbar-menu-anchor">
            <button
              type="button"
              className="account-button"
              onClick={() => {
                setAccountOpen((value) => !value);
                setNotificationOpen(false);
              }}
            >
              <Avatar profile={profile} size="small" />
              <span>
                <strong>{profile?.display_name || profile?.username}</strong>
                <small>{profile?.badge || "عضو PolyLife"}</small>
              </span>
              <ChevronDown size={16} />
            </button>
            {accountOpen && (
              <div className="topbar-dropdown account-dropdown">
                <div className="account-dropdown__identity">
                  <Avatar profile={profile} />
                  <span>
                    <strong>{profile?.display_name || profile?.username}</strong>
                    <small>@{profile?.username}</small>
                  </span>
                </div>
                <button type="button" onClick={() => navigate("profile")}>
                  <CircleUserRound size={18} />
                  پروفایل و فعالیت‌های من
                </button>
                <button type="button" onClick={() => navigate("messages")}>
                  <MessageCircle size={18} />
                  پیام‌های مستقیم
                </button>
                <button type="button" onClick={() => navigate("cart")}>
                  <ShoppingBag size={18} />
                  سبد خرید
                </button>
                <button type="button" onClick={() => navigate("transactions")}>
                  <ReceiptText size={18} />
                  تراکنش‌ها و خریدها
                </button>
                <button type="button" onClick={() => navigate("activity")}>
                  <Activity size={18} />
                  همه فعالیت‌ها
                </button>
                <button type="button" className="account-dropdown__logout" onClick={logout}>
                  <LogOut size={18} />
                  خروج از حساب
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <aside className={`sidebar ${mobileOpen ? "sidebar--open" : ""}`}>
        <nav aria-label="منوی اصلی">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={active === id ? "nav-item nav-item--active" : "nav-item"}
              onClick={() => navigate(id)}
            >
              <Icon size={20} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        {canCreate && (
          <div className="sidebar__studio">
            <span className="eyebrow">پنل متخصص</span>
            <strong>دانشت را منتشر کن</strong>
            <p>مقاله، ویدیو و دوره‌ی آموزشی بساز.</p>
            <button type="button" className="button button--cream" onClick={() => navigate("studio")}>
              <PenSquare size={17} />
              استودیوی محتوا
            </button>
          </div>
        )}

        <div className="sidebar__footer">
          <span>گروه ۸ · موضوع ۳</span>
          <small>Amirhossein Bagheri · 40031701</small>
        </div>
      </aside>

      {mobileOpen && (
        <button
          type="button"
          className="page-scrim"
          aria-label="بستن منو"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <main id="main-content" className="main-content">
        {children}
      </main>

      <nav className="bottom-nav" aria-label="منوی موبایل">
        {navigation.slice(0, 5).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={active === id ? "bottom-nav__item active" : "bottom-nav__item"}
            onClick={() => navigate(id)}
          >
            <Icon size={20} />
            <span>{label.split(" ")[0]}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
